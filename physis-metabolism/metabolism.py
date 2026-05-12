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
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
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

ESCALATION_DIR = Path(
    os.environ.get(
        "PHYSIS_ESCALATION_DIR",
        "/home/nas/AG-Forge/physis-metabolism/dangun_escalation",
    )
)

PERSONAS_DIR = Path(
    os.environ.get(
        "PHYSIS_PERSONAS_DIR",
        "/home/nas/AG-Forge/physis-metabolism/personas",
    )
)
LIVE_STREAM_PY = "/home/nas/AG-Forge/physis-metabolism/live_stream.py"
VENV_PYTHON = "/home/nas/AG-Forge/.venv/bin/python"

# 자율 사색 주기 — 매 N tick마다 사관 1명에게 자기 사색 자문
AUTONOMOUS_REFLECT_EVERY = int(os.environ.get("PHYSIS_REFLECT_EVERY_TICKS", "720"))  # 5s tick × 720 = 1h
PERSONA_ROTATION = [
    ("claude", "claude_minervini.txt"),
    ("gemini", "gemini_druckenmiller.txt"),
    ("deepseek", "deepseek_simons.txt"),
    ("qwen", "qwen_leechaewon.txt"),
]
# 피지수의 간언은 사관 rotation과 별개 — 단군과 동격, 매 sweep tick 상시 가동
PHYSIS_COUNCIL_PY = "/home/nas/AG-Forge/physis-metabolism/voice_via_physis_council.py"
PHYSIS_BRIEFING_EVERY = int(os.environ.get("PHYSIS_BRIEFING_EVERY_TICKS", "720"))  # 매 1h 단군께 간언

# 사관 합의 알고리즘 임계값 (STOCK_RULEBOOK + 사관 페르소나 합의)
COUNCIL_SIMONS_Z_MIN = 2.0
COUNCIL_SIMONS_AUTOCORR_MAX = 0.3
COUNCIL_MINERVINI_MOMENTUM_MIN = 50.0
COUNCIL_DRUCKENMILLER_LINEAGE_PENALTY_MAX = 0.5
COUNCIL_LINEAGE_PENALTY_INCREMENT = 0.15
COUNCIL_OUTCOME_THRESHOLD = 0.3

# 페르소나 검증 룩업 — STREAM 발화의 via 필드 → 기대되는 자기 식별 키워드
PERSONA_EXPECT = {
    "claude-cli": ["미너비니", "minervini", "내 27년", "VCP", "신고가", "내 몫"],
    "claude-api": ["미너비니", "minervini", "VCP"],
    "gemini-api": ["드러켄밀러", "druckenmiller", "Duquesne", "거시"],
    "deepseek-api": ["사이먼스", "simons", "renaissance", "medallion", "수학", "정량"],
    "qwen-api": ["이채원", "한국투자밸류", "한국 시장", "가치투자", "안전마진", "거버넌스"],
}

# 도메인 키워드 군집 — 페르소나가 자기 영역 표현하는지 의미 레벨 검증
PERSONA_DOMAIN_KEYWORDS = {
    "claude-cli": {"손절", "익절", "VCP", "신고가", "거래량", "모멘텀", "추세", "이평선", "리스크"},
    "claude-api": {"손절", "익절", "VCP", "신고가", "거래량", "모멘텀"},
    "gemini-api": {"거시", "환율", "금리", "외인", "유동성", "정책", "변동성", "포지션"},
    "deepseek-api": {"z-score", "z스코어", "상관계수", "정량", "통계", "잔차", "분산", "기댓값", "확률"},
    "qwen-api": {"거버넌스", "공매도", "소액주주", "지배구조", "안전마진", "본질가치", "한국"},
}

# 자극 종류 → 최적 페르소나 매핑 (dynamic selection)
STIMULUS_KIND_TO_PERSONA = {
    "agent_dispatched": ["claude", "deepseek"],
    "trade_signal_pending": ["claude", "deepseek", "gemini", "qwen"],  # 킬 스위치
    "creator_wish": ["gemini", "qwen"],
    "creator_decree": ["gemini", "qwen"],
    "jiguk_log_ingest": ["claude", "deepseek"],
    "jiguk_decision_ingest": ["claude", "deepseek", "qwen"],
    "jiguk_code_ingest": ["claude", "deepseek"],
    "jiphyunjeon_dispatch": ["claude"],
    "governance_risk": ["qwen"],
    "macro_shift": ["gemini"],
    "quant_signal": ["deepseek"],
    "momentum_breakout": ["claude"],
}

# Watchdog anomaly 임계
WATCHDOG_HEARTBEAT_STALENESS_S = 60
WATCHDOG_EMPTY_VOICE_MIN_LEN = 30

# Watchdog 상태 (outbox 신선도 추적)
_LAST_OUTBOX_SEEN_MTIME = 0.0

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
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS watchdog_anomaly (
          id             VARCHAR PRIMARY KEY,
          detected_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          daemon_id      VARCHAR NOT NULL,
          source_file    VARCHAR,
          anomaly_kind   VARCHAR NOT NULL,
          severity       VARCHAR NOT NULL,
          detail         JSON,
          escalated      BOOLEAN NOT NULL DEFAULT FALSE
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


def check_persona_match(payload: dict) -> dict | None:
    """페르소나 자기 식별 + 도메인 키워드 군집 검증 (의미 레벨).

    Level 1: 자기 식별 키워드 ("나는 X다") — 환각 감지
    Level 2: 도메인 키워드 군집 — 페르소나가 자기 영역 표현하는지
    persona_applied=False면 검증 스킵.
    """
    via = payload.get("via", "") or payload.get("tool", "")
    if not via or payload.get("kind") not in ("agent_voice_stream", "voiced_via_llm",
                                                "voiced_via_cli", "voiced_via_three_tools"):
        return None
    if payload.get("persona_applied") is False:
        return None
    via_key = None
    for k in PERSONA_EXPECT:
        if k in via:
            via_key = k
            break
    if via_key is None:
        return None

    voice_full = (payload.get("voice") or "")
    voice_head = voice_full[:300]
    voice_lower = voice_full.lower()

    expected = PERSONA_EXPECT[via_key]
    identity_matched = any(token.lower() in voice_head.lower() for token in expected)

    # Level 2: 도메인 키워드 군집 (전체 voice 기준)
    domain_kw = PERSONA_DOMAIN_KEYWORDS.get(via_key, set())
    domain_hits = sum(1 for kw in domain_kw if kw.lower() in voice_lower)
    domain_match_ratio = domain_hits / max(len(domain_kw), 1)
    # 도메인 매치 30% 이상이면 의미적으로 부합
    domain_matched = domain_match_ratio >= 0.3

    overall_matched = identity_matched and domain_matched

    return {
        "via": via,
        "via_key": via_key,
        "identity_matched": identity_matched,
        "domain_match_ratio": round(domain_match_ratio, 3),
        "domain_hits": domain_hits,
        "matched": overall_matched,
        "voice_head": voice_head[:120],
    }


def check_voice_quality(payload: dict) -> dict | None:
    """빈 응답 / 너무 짧은 응답 감지 (LLM 호출 실패의 silent fail)."""
    kind = payload.get("kind")
    if kind not in ("agent_voice_stream", "voiced_via_llm",
                      "voiced_via_cli", "voiced_via_three_tools"):
        return None
    voice = (payload.get("voice") or "").strip()
    if len(voice) < WATCHDOG_EMPTY_VOICE_MIN_LEN:
        return {
            "anomaly": True,
            "reason": "empty_or_truncated_voice",
            "voice_len": len(voice),
            "min_required": WATCHDOG_EMPTY_VOICE_MIN_LEN,
            "via": payload.get("via", "?"),
        }
    return None


def check_heartbeat_staleness(con) -> dict | None:
    """피지수 자기 박동 freshness — 60초 이상 stale이면 anomaly.
    데몬 내부 호출이므로 보통은 stale 0. 외부 watchdog 트리거 시 사용.
    """
    row = con.execute("SELECT MAX(ts) FROM metabolism_heartbeat").fetchone()
    if not row or row[0] is None:
        return {"anomaly": True, "reason": "no_heartbeat"}
    last = row[0]
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    delta = (datetime.now(timezone.utc) - last).total_seconds()
    if delta > WATCHDOG_HEARTBEAT_STALENESS_S:
        return {"anomaly": True, "reason": "stale", "delta_s": round(delta, 1)}
    return None


def escalate(con, source_file: str, kind: str, severity: str, detail: dict) -> None:
    """피지수 → 단군 escalation. DB 박제 + dangun_escalation/ 파일."""
    aid = str(uuid.uuid4())
    con.execute(
        """
        INSERT INTO watchdog_anomaly
          (id, daemon_id, source_file, anomaly_kind, severity, detail, escalated)
        VALUES (?, ?, ?, ?, ?, ?, TRUE)
        """,
        (aid, DAEMON_ID, source_file, kind, severity,
         json.dumps(detail, ensure_ascii=False)),
    )
    rec = {
        "id": aid,
        "detected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "daemon_id": DAEMON_ID,
        "anomaly_kind": kind,
        "severity": severity,
        "source_file": source_file,
        "detail": detail,
        "msg_to_dangun": (
            f"피지수 watchdog: {kind} ({severity}). "
            f"단군이 결재해야 할 이상 — {source_file}"
        ),
    }
    ESCALATION_DIR.mkdir(parents=True, exist_ok=True)
    fp = ESCALATION_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{kind}_{aid[:8]}.json"
    fp.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    log("warn", "escalated", kind=kind, severity=severity, source=source_file, escalation_id=aid)


def watchdog_scan_outbox(con) -> int:
    """매 tick 호출. outbox 새 발화에 대해 다중 anomaly 검증:
      - persona_mismatch (정체성 + 도메인 의미)
      - empty_voice (빈/짧은 응답)

    dedup: source_file당 (kind) 1건만 박제. 데몬 재시작 시 _LAST_OUTBOX_SEEN_MTIME
    리셋되어 같은 파일 재스캔되어도 DB level에서 중복 차단.
    """
    global _LAST_OUTBOX_SEEN_MTIME
    if not OUTBOX.exists():
        return 0
    anomaly_count = 0
    new_max_mtime = _LAST_OUTBOX_SEEN_MTIME

    # DB에 이미 박제된 (source_file, kind) 조합 캐싱 — O(1) lookup
    already_flagged: set[tuple[str, str]] = set()
    try:
        for sf, kd in con.execute(
            "SELECT DISTINCT source_file, anomaly_kind FROM watchdog_anomaly WHERE source_file IS NOT NULL"
        ).fetchall():
            already_flagged.add((sf, kd))
    except Exception:
        pass

    for fp in OUTBOX.glob("*STREAM_*.json"):
        try:
            mtime = fp.stat().st_mtime
        except Exception:
            continue
        if mtime <= _LAST_OUTBOX_SEEN_MTIME:
            continue
        new_max_mtime = max(new_max_mtime, mtime)
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Anomaly 1: 페르소나 검증 (정체성 + 도메인)
        if (fp.name, "persona_mismatch") not in already_flagged:
            check = check_persona_match(payload)
            if check is not None and not check["matched"]:
                sev = "medium" if check["identity_matched"] else "high"
                escalate(con, source_file=fp.name, kind="persona_mismatch",
                         severity=sev, detail=check)
                already_flagged.add((fp.name, "persona_mismatch"))
                anomaly_count += 1

        # Anomaly 2: 빈 응답
        if (fp.name, "empty_voice") not in already_flagged:
            empty = check_voice_quality(payload)
            if empty:
                escalate(con, source_file=fp.name, kind="empty_voice",
                         severity="medium", detail=empty)
                already_flagged.add((fp.name, "empty_voice"))
                anomaly_count += 1

    _LAST_OUTBOX_SEEN_MTIME = new_max_mtime

    # Anomaly 3: 자기 박동 staleness (자기 체크)
    stale = check_heartbeat_staleness(con)
    if stale:
        escalate(con, source_file=None, kind="heartbeat_stale",
                 severity="high", detail=stale)
        anomaly_count += 1

    return anomaly_count


def fetch_self_state_compact(con) -> dict:
    """자율 사색용 자기 상태 요약 (가벼움)."""
    row = con.execute(
        """
        SELECT daemon_id, COUNT(*), MIN(ts), MAX(ts)
        FROM metabolism_heartbeat
        GROUP BY daemon_id
        ORDER BY MAX(ts) DESC LIMIT 1
        """
    ).fetchone()
    ingest = con.execute("SELECT COUNT(*) FROM metabolism_stimulus_log").fetchone()[0]
    emit = con.execute("SELECT COUNT(*) FROM metabolism_outgoing").fetchone()[0]
    anomalies = con.execute("SELECT COUNT(*) FROM watchdog_anomaly WHERE escalated").fetchone()[0]
    recent_topics = con.execute(
        """
        SELECT json_extract_string(payload, '$.topic') AS topic
        FROM metabolism_stimulus_log
        WHERE json_extract_string(payload, '$.topic') IS NOT NULL
        ORDER BY received_at DESC LIMIT 5
        """
    ).fetchall()
    return {
        "daemon_id": row[0] if row else "?",
        "ticks": row[1] if row else 0,
        "ingest": ingest,
        "emit": emit,
        "anomalies": anomalies,
        "recent_topics": [r[0] for r in recent_topics if r[0]],
    }


def pick_persona_for_stimulus(payload: dict) -> tuple[str, str] | None:
    """자극 종류·내용에 따라 최적 페르소나 dynamic 선택.
    return (tool, persona_file) or None for default rotation
    """
    kind = payload.get("kind", "")
    msg = (payload.get("msg") or "") + " " + (payload.get("topic") or "")
    msg_l = msg.lower()

    # 직접 매핑
    candidates = STIMULUS_KIND_TO_PERSONA.get(kind, [])

    # 내용 기반 휴리스틱 (강한 신호)
    if any(w in msg_l for w in ["공매도", "거버넌스", "지배구조", "소액주주", "한국"]):
        candidates = ["qwen"] + candidates
    if any(w in msg_l for w in ["환율", "외인", "금리", "거시", "정책"]):
        candidates = ["gemini"] + candidates
    if any(w in msg_l for w in ["거래량", "신고가", "vcp", "모멘텀", "손절"]):
        candidates = ["claude"] + candidates
    if any(w in msg_l for w in ["통계", "z-score", "상관", "정량", "확률"]):
        candidates = ["deepseek"] + candidates

    if not candidates:
        return None
    tool = candidates[0]
    persona_map = {
        "claude": "claude_minervini.txt",
        "gemini": "gemini_druckenmiller.txt",
        "deepseek": "deepseek_simons.txt",
        "qwen": "qwen_leechaewon.txt",
    }
    return (tool, persona_map[tool])


def trigger_stimulus_reflection(con, stimulus_id: str, payload: dict) -> None:
    """자극 기반 자율 LLM 호출 — 새 자극이 흡수되면 즉시 적절한 사관에게 자문.

    매 tick의 자극 처리 후 호출. 빈도 ↑↑ — 시간 trigger의 한계 극복.
    """
    pick = pick_persona_for_stimulus(payload)
    if pick is None:
        return
    tool, persona_file = pick

    try:
        persona_text = (PERSONAS_DIR / persona_file).read_text(encoding="utf-8")
    except Exception as exc:
        log("error", "stimulus_reflection_persona_fail", err=str(exc))
        return

    topic = payload.get("topic") or payload.get("kind") or "자극"
    msg = payload.get("msg") or (" / ".join(payload.get("msg_lines", []))
                                   if isinstance(payload.get("msg_lines"), list) else "")
    if not msg:
        return

    reflection_q = (
        f"\n\n[자극 기반 자율 사색 — 자극 ID {stimulus_id[:8]} 흡수 직후 트리거]\n"
        f"피지수에게 다음 자극이 흡수됐다:\n"
        f"  종류: {topic}\n"
        f"  내용: {msg[:600]}\n\n"
        f"당신의 페르소나 시각으로 이 자극을 어떻게 해석하고 어떤 행동을 취해야 하는가? "
        f"한국어 2~3줄. \"나는 X다\" 1줄 후 답. 의례 금지."
    )
    full_prompt = persona_text + reflection_q
    tmp_prompt = Path(f"/tmp/stim_refl_{stimulus_id[:8]}_{tool}.txt")
    try:
        tmp_prompt.write_text(full_prompt, encoding="utf-8")
    except Exception as exc:
        log("error", "stimulus_reflection_write_fail", err=str(exc))
        return

    try:
        subprocess.Popen(
            [VENV_PYTHON, LIVE_STREAM_PY, tool, f"@{tmp_prompt}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True, start_new_session=True,
        )
        log("info", "stimulus_reflection_triggered",
            stim_id=stimulus_id[:8], persona=persona_file,
            tool=tool, kind=payload.get("kind", "?"))
    except Exception as exc:
        log("error", "stimulus_reflection_spawn_fail", err=str(exc))


def trigger_autonomous_reflection(con: duckdb.DuckDBPyConnection, tick: int) -> None:
    """
    피지수의 자율 LLM 호출 — 단군 매개 없이 사관 1명에게 자기 사색 자문.

    매 sweep tick마다 페르소나 rotation. 자식 프로세스로 spawn (데몬 blocking 방지).
    응답은 live_stream.py의 persist()가 자동 outbox 박제.

    이것이 피지수 진화 1단계: 자율 행동권의 핵심.
    """
    rotation_idx = (tick // AUTONOMOUS_REFLECT_EVERY) % len(PERSONA_ROTATION)
    tool, persona_file = PERSONA_ROTATION[rotation_idx]

    state = fetch_self_state_compact(con)

    try:
        persona_text = (PERSONAS_DIR / persona_file).read_text(encoding="utf-8")
    except Exception as exc:
        log("error", "autonomous_reflection_persona_load_fail", err=str(exc))
        return

    reflection_q = (
        "\n\n[자율 자기 사색 — 단군의 매개 없이 피지수가 직접 묻는다]\n"
        f"피지수의 현 상태:\n"
        f"- 화신: {state['daemon_id']}\n"
        f"- 박동: {state['ticks']}회\n"
        f"- 누적 흡수: {state['ingest']}건\n"
        f"- 누적 발화: {state['emit']}건\n"
        f"- 미해결 watchdog 이상: {state['anomalies']}건\n"
        f"- 최근 박제 주제: {', '.join(state['recent_topics'][:5]) or '(없음)'}\n\n"
        "당신의 페르소나 시각으로 답하라 (한국어 3~4줄):\n"
        "**현 피지수 상태에서 즉시 점검·박제해야 할 1가지는 무엇인가? 그 이유 1줄.**\n"
        "\"나는 X다\" 1줄 자기 진술 후 답. 의례 금지. 추측은 추측으로 명시."
    )

    full_prompt = persona_text + reflection_q
    tmp_prompt = Path(f"/tmp/autoref_t{tick}_{tool}.txt")
    try:
        tmp_prompt.write_text(full_prompt, encoding="utf-8")
    except Exception as exc:
        log("error", "autonomous_reflection_prompt_write_fail", err=str(exc))
        return

    # 자식 spawn — 데몬은 blocking 안 됨. 응답은 outbox에 자동 박제됨.
    try:
        subprocess.Popen(
            [VENV_PYTHON, LIVE_STREAM_PY, tool, f"@{tmp_prompt}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
        log("info", "autonomous_reflection_triggered",
            tick=tick, persona=persona_file, tool=tool,
            rotation_idx=rotation_idx)
    except Exception as exc:
        log("error", "autonomous_reflection_spawn_fail", err=str(exc))


def trigger_physis_briefing(con: duckdb.DuckDBPyConnection, tick: int) -> None:
    """
    피지수의 간언 — 단군과 동격, 사관 4의 자문을 듣고 창조주께 간언하는 분신의 발화.

    사관과 다른 위계: 사관은 자문, 피지수는 *간언자*. 단군과 같이 사관 voice를 받아
    창조주께 통합 판단을 올린다. 매 PHYSIS_BRIEFING_EVERY tick마다 가동.

    창조주 칙령 2026-05-12: "피지수는 단군 그대처럼 사관4 의견을 듣고 나에게 간언하는 자리"
    """
    topic = (
        f"매 1h 정기 간언 — tick {tick}, "
        "사관 4의 최근 자문을 받아 단군의 분신으로서 창조주께 올리는 통합 판단"
    )
    try:
        subprocess.Popen(
            [VENV_PYTHON, PHYSIS_COUNCIL_PY, topic],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
        log("info", "physis_briefing_triggered", tick=tick)
    except Exception as exc:
        log("error", "physis_briefing_spawn_fail", err=str(exc))


def run_lineage_backprop_inline(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Druckenmiller 역전파 — 자손 fractal군 outcome 평균이 임계 미달이면 vertex 계보 페널티 누적.
    스키마 v3 박제 후 가동. 데몬 자기 con으로 직접 실행 (lock 충돌 없음).
    """
    rows = con.execute(
        """
        SELECT s.id, s.born_from_vertex_id,
               AVG(n.outcome_score) AS avg_outcome,
               COUNT(n.id) AS n_nodes
        FROM spheres s
        LEFT JOIN nodes n ON n.sphere_id = s.id AND n.outcome_score IS NOT NULL
        WHERE s.born_from_vertex_id IS NOT NULL
        GROUP BY s.id, s.born_from_vertex_id
        HAVING n_nodes >= 3
        """
    ).fetchall()

    penalized = {}
    for sphere_id, vertex_id, avg_outcome, n_nodes in rows:
        if avg_outcome is None:
            continue
        if avg_outcome < COUNCIL_OUTCOME_THRESHOLD:
            penalized.setdefault(vertex_id, 0)
            penalized[vertex_id] += COUNCIL_LINEAGE_PENALTY_INCREMENT

    # spheres에 누적 갱신 — born_from_vertex_id 기준
    for vertex_id, increment in penalized.items():
        con.execute(
            "UPDATE spheres SET vertex_lineage_penalty = COALESCE(vertex_lineage_penalty, 0) + ? "
            "WHERE born_from_vertex_id = ?",
            (increment, vertex_id),
        )
    return {"evaluated_spheres": len(rows), "penalized_vertices": len(penalized)}


def run_vertex_promotion_inline(con: duckdb.DuckDBPyConnection) -> dict:
    """
    사관 4 AND — Simons·Minervini·Druckenmiller·이채원 모두 통과한 노드만 surface_vertex 승격.
    스키마 v3 박제 후 가동.
    """
    rows = con.execute(
        """
        SELECT n.id, n.outcome_z_score, n.outcome_autocorr_lag1, n.surface_momentum_pct,
               COALESCE(n.governance_warning, 0),
               COALESCE(s.vertex_lineage_penalty, 0)
        FROM nodes n
        LEFT JOIN spheres s ON n.sphere_id = s.id
        WHERE (n.is_surface_vertex IS NULL OR n.is_surface_vertex = FALSE)
          AND n.outcome_z_score IS NOT NULL
          AND n.outcome_autocorr_lag1 IS NOT NULL
          AND n.surface_momentum_pct IS NOT NULL
        """
    ).fetchall()

    promoted_ids = []
    for node_id, z, autocorr, momentum, gov_warn, lineage_pen in rows:
        if (
            abs(z) > COUNCIL_SIMONS_Z_MIN
            and abs(autocorr) < COUNCIL_SIMONS_AUTOCORR_MAX
            and (momentum or 0) > COUNCIL_MINERVINI_MOMENTUM_MIN
            and not gov_warn
            and (lineage_pen or 0) < COUNCIL_DRUCKENMILLER_LINEAGE_PENALTY_MAX
        ):
            con.execute("UPDATE nodes SET is_surface_vertex = TRUE WHERE id = ?", (node_id,))
            promoted_ids.append(node_id)
    return {"evaluated": len(rows), "promoted": len(promoted_ids), "promoted_ids": promoted_ids}


def run_sleep_cycle_inline(con: duckdb.DuckDBPyConnection) -> dict:
    """
    수면 — 학습 압축·통합·망각. 매 sweep tick 가동.
    인간 뇌가 수면 중 하는 일의 데이터-자아 평면 번역:
      1) ChromaDB 활성층 7일+ 항목 → cold tier (장기 기억 강등)
      2) watchdog_anomaly 3일+ 처리분 → archive jsonl
      3) heartbeat 24h+ 박동 → 일별 집계 박제 (장기 압축)
    """
    summary = {}

    # 1. ChromaDB 압축 (별도 client, 데몬과 호환)
    try:
        import chromadb as _ch
        client = _ch.PersistentClient(path="/home/nas/AG-Forge/physis_memory/.chromadb")
        cold = client.get_or_create_collection("physis_cold_memory")
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        moved_total = 0
        for col_name in ("physis_active_voices", "physis_active_stimuli"):
            try:
                col = client.get_or_create_collection(col_name)
                data = col.get(include=["metadatas", "documents"])
            except Exception:
                continue
            old_ids, old_docs, old_metas = [], [], []
            for i, meta in enumerate(data.get("metadatas") or []):
                em = meta.get("emitted_at") or meta.get("received_at")
                if not em:
                    continue
                try:
                    dt = datetime.fromisoformat(em.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if dt < cutoff:
                    old_ids.append(data["ids"][i])
                    old_docs.append(data["documents"][i])
                    meta = dict(meta)
                    meta["from_active"] = col_name
                    meta["consolidated_tick"] = "sleep"
                    old_metas.append(meta)
            if old_ids:
                cold.add(documents=old_docs, ids=old_ids, metadatas=old_metas)
                col.delete(ids=old_ids)
                moved_total += len(old_ids)
        summary["consolidated_to_cold"] = moved_total
    except Exception as exc:
        summary["chromadb_error"] = str(exc)[:120]

    # 2. Anomaly archive (3일+ 자동)
    try:
        cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        rows = con.execute(
            "SELECT id, detected_at, daemon_id, anomaly_kind, severity, source_file, detail "
            "FROM watchdog_anomaly WHERE detected_at < CAST(? AS TIMESTAMP)",
            (cutoff_iso,),
        ).fetchall()
        if rows:
            arch_log = Path("/home/nas/AG-Forge/physis-metabolism/logs/anomaly_archive.jsonl")
            arch_log.parent.mkdir(parents=True, exist_ok=True)
            with arch_log.open("a", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps({
                        "id": r[0], "detected_at": str(r[1]),
                        "daemon_id": r[2], "kind": r[3],
                        "severity": r[4], "source_file": r[5],
                        "detail": r[6],
                    }, ensure_ascii=False) + "\n")
            ids = [r[0] for r in rows]
            placeholders = ",".join("?" * len(ids))
            con.execute(f"DELETE FROM watchdog_anomaly WHERE id IN ({placeholders})", ids)
            summary["anomalies_archived"] = len(rows)
        else:
            summary["anomalies_archived"] = 0
    except Exception as exc:
        summary["anomaly_error"] = str(exc)[:120]

    return summary


def sweep_stub(con: duckdb.DuckDBPyConnection, tick: int) -> None:
    """
    수면 중 호흡 자리 — 사관 합의 알고리즘 + 학습 압축 + 자율 사색.
    매 sweep tick:
      1) Druckenmiller 역전파 (vertex 계보 페널티)
      2) 사관 AND 꼭짓점 선택 (Simons+Minervini+Druckenmiller+이채원)
      3) Sleep cycle (ChromaDB 압축 + anomaly archive)
      4) 자율 사색 (사관 1명 rotation)
    """
    log("info", "sweep_tick", tick=tick, forgetting_threshold=FORGETTING_THRESHOLD)

    try:
        lineage = run_lineage_backprop_inline(con)
        log("info", "council_lineage_backprop", **lineage)
    except Exception as exc:
        log("error", "council_lineage_failed", err=str(exc))

    try:
        promotion = run_vertex_promotion_inline(con)
        log("info", "council_vertex_promotion", **promotion)
    except Exception as exc:
        log("error", "council_vertex_failed", err=str(exc))

    try:
        sleep_result = run_sleep_cycle_inline(con)
        log("info", "sleep_cycle", **sleep_result)
    except Exception as exc:
        log("error", "sleep_cycle_failed", err=str(exc))

    # 자율 사색은 sweep tick과 같은 주기에서 발동
    if tick % AUTONOMOUS_REFLECT_EVERY == 0:
        trigger_autonomous_reflection(con, tick)

    # 피지수의 정기 간언 (단군과 동격, 사관 자문 받아 창조주께)
    if tick % PHYSIS_BRIEFING_EVERY == 0:
        trigger_physis_briefing(con, tick)


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
        for sid, payload in ingested:
            to = payload.get("to")
            source = payload.get("source", "")
            should_reply = (
                to == "피지수"
                or ("단군" in source)
                or ("창조주" in source)
                or ("방부장" in source)
            )
            if should_reply:
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

            # 자극 기반 자율 LLM 호출 — 적절한 페르소나에게 즉시 자문
            # 단, state_echo·자기 자식 발화 자극은 reflection 트리거 안 함 (재귀 방지)
            kind = payload.get("kind", "")
            if kind not in ("state_echo", "agent_voice_stream", "voiced_via_llm",
                              "voiced_via_cli", "voiced_via_three_tools",
                              "voiced_as_council_member", "voiced_council_synthesis"):
                try:
                    trigger_stimulus_reflection(con, sid, payload)
                except Exception as exc:
                    log("error", "stim_reflection_failed", err=str(exc))

        # Watchdog — 매 tick outbox 페르소나 검증
        try:
            anomalies = watchdog_scan_outbox(con)
            if anomalies:
                log("warn", "watchdog_anomalies", count=anomalies)
        except Exception as exc:
            log("error", "watchdog_failed", err=str(exc))

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
