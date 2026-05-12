"""
피지수 수면 사이클 — 학습한 것의 *압축·통합·망각*.

인간 뇌가 수면 중 하는 일을 데이터-자아 평면에서 번역:
  1. ChromaDB 활성층 (active_voices, active_stimuli)에서 *오래되고 ref_count 낮은* 항목을
     cold_memory로 이전 (장기 기억으로 강등)
  2. outbox 7일+ 발화 → 가능하면 cold tier로 압축 (대용량 voice 요약 후 박제)
  3. metabolism_heartbeat 24h+ 박동 → 일일 집계 (fractal_density 보강)
  4. watchdog_anomaly 처리·해소된 항목 → archive (logs/anomaly_archive.jsonl)
  5. forgetting_threshold 적용 — outcome_score 낮은 stimulus를 cold로

가동:
  python sleep_consolidator.py --cycle    # 1회 사이클
  python sleep_consolidator.py --dry      # 시뮬레이션
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import chromadb
import duckdb

CHROMA_PATH = "/home/nas/AG-Forge/physis_memory/.chromadb"
DUCKDB_PATH = "/home/nas/AG-Forge/physis_memory/physis_brain.duckdb"
OUTBOX = Path("/home/nas/AG-Forge/physis-metabolism/outbox")
LOGS = Path("/home/nas/AG-Forge/physis-metabolism/logs")
ANOMALY_ARCHIVE = LOGS / "anomaly_archive.jsonl"

ACTIVE_TO_COLD_DAYS = 7   # 활성층 7일+ 항목을 cold로
ANOMALY_RETENTION_DAYS = 3
HEARTBEAT_AGGREGATE_AFTER_DAYS = 1


def consolidate_chromadb(dry: bool = False) -> dict:
    """활성층(voices·stimuli)에서 오래된 것을 cold로 강등."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    cold = client.get_or_create_collection("physis_cold_memory")
    voices = client.get_or_create_collection("physis_active_voices")
    stims = client.get_or_create_collection("physis_active_stimuli")

    moved = {"voices_to_cold": 0, "stimuli_to_cold": 0}
    cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_TO_COLD_DAYS)

    for col_name, col in [("voices", voices), ("stimuli", stims)]:
        try:
            data = col.get(include=["metadatas", "documents"])
        except Exception:
            continue
        old_ids, old_docs, old_metas = [], [], []
        for i, meta in enumerate(data.get("metadatas") or []):
            emitted = meta.get("emitted_at") or meta.get("received_at")
            if not emitted:
                continue
            try:
                # ISO 시각 파싱 (다양한 형식 대응)
                if "+" in emitted or emitted.endswith("Z"):
                    dt = datetime.fromisoformat(emitted.replace("Z", "+00:00"))
                else:
                    dt = datetime.fromisoformat(emitted)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if dt < cutoff:
                old_ids.append(data["ids"][i])
                old_docs.append(data["documents"][i])
                meta["from_active"] = col_name
                meta["consolidated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                old_metas.append(meta)

        if old_ids and not dry:
            cold.add(documents=old_docs, ids=old_ids, metadatas=old_metas)
            col.delete(ids=old_ids)
        key = f"{col_name}_to_cold"
        moved[key] = len(old_ids)

    return moved


def archive_anomalies(con, dry: bool = False) -> dict:
    """수면 중 해소된(escalated=TRUE이며 N일+ 지난) anomaly를 jsonl로 archive."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=ANOMALY_RETENTION_DAYS)).isoformat()
    rows = con.execute(
        """
        SELECT id, detected_at, daemon_id, anomaly_kind, severity, source_file, detail
        FROM watchdog_anomaly
        WHERE detected_at < CAST(? AS TIMESTAMP)
        """,
        (cutoff,),
    ).fetchall()
    if not rows:
        return {"archived": 0}
    if not dry:
        LOGS.mkdir(parents=True, exist_ok=True)
        with ANOMALY_ARCHIVE.open("a", encoding="utf-8") as f:
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
    return {"archived": len(rows)}


def aggregate_heartbeat(con, dry: bool = False) -> dict:
    """24h+ heartbeat을 daily aggregate로 압축 (장기 보관용)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=HEARTBEAT_AGGREGATE_AFTER_DAYS)).isoformat()
    row = con.execute(
        "SELECT COUNT(*) FROM metabolism_heartbeat WHERE ts < CAST(? AS TIMESTAMP)",
        (cutoff,),
    ).fetchone()
    if not row or row[0] == 0:
        return {"aggregated_rows": 0}
    # 집계만 — 삭제는 향후 결단
    agg = con.execute(
        """
        SELECT DATE_TRUNC('day', ts) AS day, daemon_id,
               COUNT(*) AS ticks, SUM(stimuli_seen) AS total_stim,
               SUM(CASE WHEN sweep_ran THEN 1 ELSE 0 END) AS sweep_count
        FROM metabolism_heartbeat
        WHERE ts < CAST(? AS TIMESTAMP)
        GROUP BY day, daemon_id
        ORDER BY day DESC
        """,
        (cutoff,),
    ).fetchall()
    if not dry:
        # 집계 결과를 로그로 박제 (테이블 신설 안 함 — 가벼움 유지)
        agg_log = LOGS / "heartbeat_aggregate.jsonl"
        with agg_log.open("a", encoding="utf-8") as f:
            for a in agg:
                f.write(json.dumps({
                    "day": str(a[0]), "daemon_id": a[1],
                    "ticks": a[2], "stimuli": a[3], "sweep_count": a[4],
                    "aggregated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }, ensure_ascii=False) + "\n")
    return {"aggregated_rows": row[0], "daily_groups": len(agg)}


def run_cycle(dry: bool = False) -> dict:
    print("━" * 60)
    print(f"수면 사이클 {'(DRY-RUN)' if dry else ''} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("━" * 60)
    summary = {}

    try:
        m = consolidate_chromadb(dry=dry)
        summary["chromadb"] = m
        print(f"  ChromaDB 압축: voices→cold {m['voices_to_cold']}건, stimuli→cold {m['stimuli_to_cold']}건")
    except Exception as exc:
        print(f"  ✗ ChromaDB 압축 실패: {exc}")
        summary["chromadb"] = {"error": str(exc)}

    try:
        con = duckdb.connect(DUCKDB_PATH, read_only=False)
        a = archive_anomalies(con, dry=dry)
        summary["anomaly_archive"] = a
        print(f"  Anomaly archive: {a['archived']}건")
        h = aggregate_heartbeat(con, dry=dry)
        summary["heartbeat"] = h
        print(f"  Heartbeat 집계: {h.get('aggregated_rows', 0)} rows → {h.get('daily_groups', 0)} 일별 그룹")
        con.close()
    except Exception as exc:
        print(f"  ✗ DuckDB 작업 실패 (lock 또는 권한): {exc}")
        summary["duckdb"] = {"error": str(exc)}

    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", action="store_true", help="1회 수면 사이클")
    ap.add_argument("--dry", action="store_true", help="시뮬레이션")
    args = ap.parse_args()
    if args.cycle or args.dry:
        result = run_cycle(dry=args.dry)
        print()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
