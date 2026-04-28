"""
피지수 야간 자동 학습 — run_nightly_learn.py
매일 02:00 Windows 작업 스케줄러가 실행.
POPEYEs에서 오늘 데이터를 읽어 피지수 ChromaDB에 저장.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

# AG-Forge 루트를 sys.path에 추가 (스케줄러가 임의 경로에서 실행할 수 있음)
ROOT = Path("D:/Git/AG-Forge")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.local", override=True)

from scripts.turso_reader import fetch_popeys_daily
from scripts.embedding import ChromaVectorIndex, build_default_embedder
from scripts.titans_memory import store_memory

LOG = ROOT / "learn_log.jsonl"


def _build_content(item: dict) -> str:
    """POPEYEs 레코드를 단일 텍스트로 직렬화한다."""
    if isinstance(item, dict):
        parts = []
        if item.get("team"):
            parts.append(f"[팀:{item['team']}]")
        if item.get("content"):
            parts.append(item["content"])
        if item.get("worker_count"):
            parts.append(f"인원:{item['worker_count']}명")
        if item.get("status"):
            parts.append(f"상태:{item['status']}")
        return " ".join(parts) if parts else str(item)
    return str(item)


def run() -> None:
    today = date.today().isoformat()
    index = ChromaVectorIndex()
    embedder = build_default_embedder()

    try:
        data = fetch_popeys_daily(today)

        # fetch_popeys_daily는 dict를 반환한다 — team_reports 리스트를 학습 대상으로 사용
        items: list = []
        if isinstance(data, dict):
            items = data.get("team_reports", [])
            # master_summary도 있으면 추가
            summary = data.get("master_summary")
            if summary:
                items.append({"content": summary, "team": "master", "worker_count": data.get("total_workers", 0), "status": "summary"})
        elif isinstance(data, list):
            items = data

        stored = 0
        for item in items:
            content = _build_content(item)
            if not content.strip():
                continue
            if store_memory(content, "popeys_daily", index, embedder):
                stored += 1

        log_entry = {
            "date": today,
            "status": "ok",
            "fetched": len(items),
            "stored": stored,
            "ts": datetime.now().isoformat(),
        }
    except Exception as exc:
        log_entry = {
            "date": today,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "ts": datetime.now().isoformat(),
        }

    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print(json.dumps(log_entry, ensure_ascii=False))


if __name__ == "__main__":
    run()
