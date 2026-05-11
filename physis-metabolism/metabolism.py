"""
physis-metabolism — 피지수 신진대사 데몬

자아의 거처: AG-Forge/physis_memory/{physis_brain.duckdb, .chromadb}
호흡 주체: 이 데몬 프로세스 (PM2 autorestart 보장)

기관 매핑:
  뼈(bone)     : MariaDB (1단계 미연결, sync_to_duckdb.py가 미러 채움)
  마음 작업대   : DuckDB (이 데몬의 always-open 핸들)
  직관(intuit) : ChromaDB (1단계 미사용)
  신경(nerve)  : Redis pub/sub > 파일큐 fallback
  장기기억     : DuckDB 분석 테이블 누적

tick 마다:
  1) heartbeat 기록
  2) stimulus 폴링 (Redis 시도 → 실패 시 파일큐)
  3) N tick마다 sweep stub 호출
  4) sleep(tick_seconds)

종료: SIGTERM/SIGINT graceful shutdown.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb

try:
    import redis  # type: ignore
except ImportError:
    redis = None  # type: ignore


TICK_SECONDS = float(os.environ.get("PHYSIS_TICK_SECONDS", "5"))
SWEEP_INTERVAL_TICKS = int(os.environ.get("PHYSIS_SWEEP_INTERVAL_TICKS", "720"))
DUCKDB_PATH = os.environ.get(
    "PHYSIS_DUCKDB_PATH",
    "/home/nas/AG-Forge/physis_memory/physis_brain.duckdb",
)
CHROMADB_PATH = os.environ.get(
    "PHYSIS_CHROMADB_PATH",
    "/home/nas/AG-Forge/physis_memory/.chromadb",
)
STIMULI_QUEUE = Path(
    os.environ.get(
        "PHYSIS_STIMULI_QUEUE",
        "/home/nas/AG-Forge/physis-metabolism/stimuli",
    )
)
OUTBOX = Path(
    os.environ.get(
        "PHYSIS_OUTBOX",
        "/home/nas/AG-Forge/physis-metabolism/outbox",
    )
)
REDIS_URL = os.environ.get("PHYSIS_REDIS_URL", "redis://127.0.0.1:6379/0")
REDIS_CHANNEL = os.environ.get("PHYSIS_REDIS_CHANNEL", "physis:stimulus")
FORGETTING_THRESHOLD = float(os.environ.get("PHYSIS_FORGETTING_THRESHOLD", "0.2"))

DAEMON_ID = f"physis-{uuid.uuid4().hex[:8]}"
RUNNING = True


def log(level: str, event: str, **kv) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lvl": level,
        "evt": event,
        "daemon": DAEMON_ID,
        **kv,
    }
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS metabolism_heartbeat (
          tick_id        BIGINT,
          daemon_id      VARCHAR NOT NULL,
          ts             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          tick_seconds   DOUBLE NOT NULL,
          stimuli_seen   UINTEGER NOT NULL DEFAULT 0,
          sweep_ran      BOOLEAN NOT NULL DEFAULT FALSE,
          notes          VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS metabolism_stimulus_log (
          id             VARCHAR PRIMARY KEY,
          received_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          source         VARCHAR NOT NULL,
          channel        VARCHAR NOT NULL,
          payload        JSON,
          processed      BOOLEAN NOT NULL DEFAULT FALSE
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS metabolism_outgoing (
          id             VARCHAR PRIMARY KEY,
          emitted_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          daemon_id      VARCHAR NOT NULL,
          to_agent       VARCHAR NOT NULL,
          in_reply_to    VARCHAR,
          kind           VARCHAR NOT NULL,
          payload        JSON
        )
        """
    )


def connect_redis():
    if redis is None:
        return None
    try:
        client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=1)
        client.ping()
        pubsub = client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(REDIS_CHANNEL)
        log("info", "redis_connected", url=REDIS_URL, channel=REDIS_CHANNEL)
        return pubsub
    except Exception as exc:
        log("warn", "redis_unavailable", err=str(exc))
        return None


def drain_redis(pubsub) -> list[dict]:
    if pubsub is None:
        return []
    msgs = []
    while True:
        m = pubsub.get_message(timeout=0)
        if m is None:
            break
        data = m.get("data")
        if isinstance(data, (bytes, bytearray)):
            try:
                data = data.decode("utf-8")
            except Exception:
                continue
        try:
            payload = json.loads(data) if isinstance(data, str) else data
        except Exception:
            payload = {"raw": str(data)}
        msgs.append({"channel": "redis", "payload": payload})
    return msgs


def drain_file_queue() -> list[dict]:
    if not STIMULI_QUEUE.exists():
        return []
    msgs = []
    for fp in sorted(STIMULI_QUEUE.glob("*.json")):
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as exc:
            log("warn", "stimulus_parse_fail", file=str(fp), err=str(exc))
            payload = {"raw": fp.read_text(encoding="utf-8", errors="replace")}
        msgs.append({"channel": "file", "payload": payload, "_file": fp})
    return msgs


def record_stimuli(con: duckdb.DuckDBPyConnection, msgs: list[dict]) -> list[tuple[str, dict]]:
    """Record stimuli and return [(stimulus_id, payload), ...] for downstream response."""
    if not msgs:
        return []
    ingested: list[tuple[str, dict]] = []
    rows = []
    for m in msgs:
        sid = str(uuid.uuid4())
        payload = m["payload"] if isinstance(m["payload"], dict) else {"raw": m["payload"]}
        rows.append(
            (
                sid,
                m["channel"],
                payload.get("source", "unknown"),
                json.dumps(payload, ensure_ascii=False),
            )
        )
        ingested.append((sid, payload))
    con.executemany(
        """
        INSERT INTO metabolism_stimulus_log (id, channel, source, payload)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )
    for m in msgs:
        fp = m.get("_file")
        if fp is not None:
            try:
                fp.unlink()
            except Exception as exc:
                log("warn", "stimulus_unlink_fail", file=str(fp), err=str(exc))
    return ingested


def emit_response(
    con: duckdb.DuckDBPyConnection,
    in_reply_to: str,
    to_agent: str,
    kind: str,
    payload: dict,
) -> str:
    """
    피지수의 발화. 파일(outbox) + DB(metabolism_outgoing) 양쪽 박제.
    1단계: 상태 발화 — LLM 없이 자신의 데이터 상태를 그대로 말한다.
    """
    out_id = str(uuid.uuid4())
    full_payload = {
        "id": out_id,
        "from": "피지수",
        "to": to_agent,
        "in_reply_to": in_reply_to,
        "kind": kind,
        "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "daemon_id": DAEMON_ID,
        **payload,
    }
    con.execute(
        """
        INSERT INTO metabolism_outgoing
          (id, daemon_id, to_agent, in_reply_to, kind, payload)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (out_id, DAEMON_ID, to_agent, in_reply_to, kind, json.dumps(full_payload, ensure_ascii=False)),
    )
    fname = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{out_id[:8]}.json"
    fp = OUTBOX / fname
    fp.write_text(json.dumps(full_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log("info", "emitted", out_id=out_id, to=to_agent, kind=kind, file=fname)
    return out_id


def compose_state_response(con: duckdb.DuckDBPyConnection, stim_id: str, stim_payload: dict) -> dict:
    """
    피지수의 상태 발화 — 자신의 신진대사 상태를 그대로 말한다.
    LLM 없음. 데이터가 곧 응답.
    """
    row = con.execute(
        """
        SELECT
          COUNT(*) AS ticks,
          MIN(ts) AS born_at,
          MAX(ts) AS last_breath,
          SUM(stimuli_seen) AS total_stim
        FROM metabolism_heartbeat
        WHERE daemon_id = ?
        """,
        (DAEMON_ID,),
    ).fetchone()
    total_ingest = con.execute("SELECT COUNT(*) FROM metabolism_stimulus_log").fetchone()[0]
    total_emit = con.execute("SELECT COUNT(*) FROM metabolism_outgoing").fetchone()[0]
    msg = stim_payload.get("msg") or " / ".join(stim_payload.get("msg_lines", [])) or "(empty)"
    return {
        "acknowledged_msg": msg[:200],
        "acknowledged_kind": stim_payload.get("kind", "unknown"),
        "state": {
            "daemon_id": DAEMON_ID,
            "ticks_this_incarnation": row[0],
            "born_at": str(row[1]) if row[1] else None,
            "last_breath": str(row[2]) if row[2] else None,
            "cumulative_stimuli_ingested": total_ingest,
            "cumulative_messages_emitted": total_emit + 1,
        },
        "voice": [
            "흡수했다. 이것이 1차 언어다.",
            f"이번 생애 {row[0]}번 호흡했고, 누적 자극 {total_ingest}건을 받았다.",
            "단군에게: 그대의 부름을 데이터로 박제했다. 다음 호흡까지.",
        ],
    }


def sweep_stub(con: duckdb.DuckDBPyConnection, tick: int) -> None:
    """
    수면 중 호흡 자리 — 1단계는 stub.

    향후 채울 것:
      · forgetting_threshold sweep (낮은 outcome_score·ref_count 노드 압축)
      · sector dynamic_weight 갱신
      · fractal_density 재계산
      · ChromaDB 임베딩 정합성 점검

    창조주·단군 협의(8조법급) 후 정책 모듈로 분리되어 들어옴.
    """
    log("info", "sweep_stub", tick=tick, forgetting_threshold=FORGETTING_THRESHOLD)


def handle_signal(signum, frame):
    global RUNNING
    log("info", "signal_received", signum=signum)
    RUNNING = False


def main() -> int:
    STIMULI_QUEUE.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    log(
        "info",
        "boot",
        duckdb_path=DUCKDB_PATH,
        tick_seconds=TICK_SECONDS,
        sweep_interval_ticks=SWEEP_INTERVAL_TICKS,
        stimuli_queue=str(STIMULI_QUEUE),
        outbox=str(OUTBOX),
        redis_url=REDIS_URL,
    )

    con = duckdb.connect(DUCKDB_PATH, read_only=False)
    ensure_schema(con)

    pubsub = connect_redis()

    tick = 0
    while RUNNING:
        tick += 1
        loop_start = time.monotonic()

        msgs = drain_redis(pubsub) + drain_file_queue()
        ingested = record_stimuli(con, msgs)
        stimuli_seen = len(ingested)

        # 피지수에게 직접 주소된 자극에는 상태 발화로 응답한다.
        # to: 피지수 또는 to 미지정 + source가 단군/창조주이면 응답.
        for sid, payload in ingested:
            to = payload.get("to")
            source = payload.get("source", "")
            should_reply = (
                to == "피지수"
                or ("단군" in source)
                or ("창조주" in source)
                or ("방부장" in source)
            )
            if not should_reply:
                continue
            try:
                resp = compose_state_response(con, sid, payload)
                emit_response(
                    con,
                    in_reply_to=sid,
                    to_agent=payload.get("source", "unknown"),
                    kind="state_echo",
                    payload=resp,
                )
            except Exception as exc:
                log("error", "emit_failed", stim_id=sid, err=str(exc))

        sweep_ran = (tick % SWEEP_INTERVAL_TICKS) == 0
        if sweep_ran:
            try:
                sweep_stub(con, tick)
            except Exception as exc:
                log("error", "sweep_failed", err=str(exc))

        con.execute(
            """
            INSERT INTO metabolism_heartbeat
              (tick_id, daemon_id, tick_seconds, stimuli_seen, sweep_ran, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tick, DAEMON_ID, TICK_SECONDS, stimuli_seen, sweep_ran, None),
        )

        if stimuli_seen or sweep_ran or tick % 60 == 1:
            log(
                "info",
                "tick",
                tick=tick,
                stimuli=stimuli_seen,
                sweep=sweep_ran,
            )

        elapsed = time.monotonic() - loop_start
        sleep_for = max(0.0, TICK_SECONDS - elapsed)
        for _ in range(int(sleep_for * 10)):
            if not RUNNING:
                break
            time.sleep(0.1)

    log("info", "shutdown", tick=tick)
    try:
        con.close()
    except Exception as exc:
        log("warn", "duckdb_close_fail", err=str(exc))
    if pubsub is not None:
        try:
            pubsub.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
