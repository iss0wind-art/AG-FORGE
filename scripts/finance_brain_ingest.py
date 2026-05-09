"""
finance_brain_ingest.py — 4지국(Stock-AI) 거래 결정 → physis_finance_brain ChromaDB 흡수

방부장 친명 2026-05-09: 4지국 데이터 검토·판단·학습.
단군 협의 청 (id 1b20bca1) 응답 대기 중이지만 자율 영역으로 컬렉션 설계 + 1차 흡수.

구조:
  컬렉션: physis_finance_brain (별도 도메인, FORGETTING_THRESHOLD 0.2 권장)
  도큐먼트: 거래 결정 1건 = 1개
  메타데이터:
    - timestamp, stock_code, stock_name
    - signal (BUY/SELL/HOLD), confidence, agreement_rate
    - gate_passed (게이트 통과 여부)
    - hitl_result (approve/reject/timeout/null)
    - models_used, market_sentiment
    - source (pipeline_log/api_call)

사용:
  python3 scripts/finance_brain_ingest.py --create        # 컬렉션 생성
  python3 scripts/finance_brain_ingest.py --ingest-log <logfile>  # 로그 흡수
  python3 scripts/finance_brain_ingest.py --query "BUY 신뢰도 70% 이상"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VECTOR_DB_PATH = ROOT / "library" / "vector_db"
COLLECTION_NAME = "physis_finance_brain"

import chromadb


def get_client():
    return chromadb.PersistentClient(path=str(VECTOR_DB_PATH))


def get_or_create_collection():
    """physis_finance_brain 컬렉션 가져오기/생성.

    메타: 도메인 격리 + 별도 forgetting threshold 표시.
    """
    client = get_client()
    coll = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "domain": "finance",
            "created": "2026-05-09",
            "creator": "physis_1.3세대",
            "forgetting_threshold": "0.2",
            "purpose": "4지국 Stock-AI 거래 결정 흡수 + 자아 학습",
            "관련_칙령": "방부장 친명 2026-05-09 + 단군 bea7a46e",
        },
    )
    return coll


def parse_pipeline_log(log_path: Path) -> list[dict]:
    """Stock-AI scheduler.out.log 파싱 → 거래 결정 레코드 리스트.

    한 결정 = (시각, 종목, 신호, 신뢰도, 합의율, 게이트통과, HITL결과)
    """
    records: list[dict] = []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    pipeline_start_re = re.compile(r"^\[(\d\d:\d\d:\d\d)\] 📡 Stock AI Pipeline 시작")
    sentiment_re = re.compile(r"^\[(\d\d:\d\d:\d\d)\]\s+→ 시장 감성: (\S+) / 선정 종목: (\d+)개")
    selected_re = re.compile(r"^\[(\d\d:\d\d:\d\d)\]\s+- (\S+?)\((\d{6})\): (.+)$")
    analysis_re = re.compile(r"^\[(\d\d:\d\d:\d\d)\]\s+분석 중: (\S+?)\((\d{6})\)")
    signal_re = re.compile(r"^\[(\d\d:\d\d:\d\d)\]\s+→ (BUY|SELL|HOLD) \| 신뢰도 (\d+)% \| 합의율 (\d+)%")
    gate_pass_re = re.compile(r"^\[(\d\d:\d\d:\d\d)\]\s+→ 텔레그램 승인 요청 발송")
    gate_skip_re = re.compile(r"^\[(\d\d:\d\d:\d\d)\]\s+→ 조건 미충족 패스")
    hitl_result_re = re.compile(r"^\[(\d\d:\d\d:\d\d)\]\s+→ (거절/보류|승인됨)")

    current_pipeline_start: str | None = None
    current_sentiment: str = "중립"
    current_stock: dict[str, Any] | None = None

    for line in lines:
        if m := pipeline_start_re.match(line):
            current_pipeline_start = m.group(1)
            continue
        if m := sentiment_re.match(line):
            current_sentiment = m.group(2)
            continue
        if m := analysis_re.match(line):
            ts, name, code = m.group(1), m.group(2), m.group(3)
            current_stock = {
                "timestamp": ts,
                "pipeline_start": current_pipeline_start,
                "stock_name": name,
                "stock_code": code,
                "market_sentiment": current_sentiment,
            }
            continue
        if m := signal_re.match(line):
            if current_stock:
                current_stock.update({
                    "signal_time": m.group(1),
                    "signal": m.group(2),
                    "confidence": int(m.group(3)) / 100,
                    "agreement_rate": int(m.group(4)) / 100,
                })
            continue
        if m := gate_pass_re.match(line):
            if current_stock:
                current_stock["gate_passed"] = True
                current_stock["request_sent_at"] = m.group(1)
            continue
        if m := gate_skip_re.match(line):
            if current_stock:
                current_stock["gate_passed"] = False
                current_stock["hitl_result"] = "n/a"
                records.append(_finalize(current_stock))
                current_stock = None
            continue
        if m := hitl_result_re.match(line):
            if current_stock and current_stock.get("gate_passed"):
                result_text = m.group(2)
                current_stock["hitl_result"] = "rejected_or_timeout" if "거절" in result_text else "approved"
                current_stock["hitl_decided_at"] = m.group(1)
                records.append(_finalize(current_stock))
                current_stock = None
            continue

    return records


def _finalize(rec: dict) -> dict:
    """완성된 레코드를 반환 (자연어 문서 + 메타 분리)."""
    doc = (
        f"{rec['stock_name']}({rec['stock_code']}) "
        f"signal={rec.get('signal','?')} "
        f"confidence={rec.get('confidence',0):.2f} "
        f"agreement={rec.get('agreement_rate',0):.2f} "
        f"gate_passed={rec.get('gate_passed', False)} "
        f"hitl={rec.get('hitl_result','n/a')} "
        f"sentiment={rec.get('market_sentiment','?')}"
    )
    rec["document"] = doc
    return rec


def ingest_records(records: list[dict], date_label: str = "2026-05-09") -> int:
    """레코드를 ChromaDB physis_finance_brain에 흡수."""
    coll = get_or_create_collection()
    docs = []
    metas = []
    ids = []
    for i, r in enumerate(records):
        rec_id = f"{date_label}_{r.get('pipeline_start','x')}_{r.get('stock_code','x')}_{i}"
        docs.append(r["document"])
        meta = {
            "date": date_label,
            "pipeline_start": str(r.get("pipeline_start", "")),
            "stock_code": str(r.get("stock_code", "")),
            "stock_name": str(r.get("stock_name", "")),
            "signal": str(r.get("signal", "?")),
            "confidence": float(r.get("confidence", 0.0)),
            "agreement_rate": float(r.get("agreement_rate", 0.0)),
            "gate_passed": bool(r.get("gate_passed", False)),
            "hitl_result": str(r.get("hitl_result", "n/a")),
            "market_sentiment": str(r.get("market_sentiment", "중립")),
            "source": "stock_ai_scheduler_log",
        }
        metas.append(meta)
        ids.append(rec_id)

    if docs:
        coll.add(documents=docs, metadatas=metas, ids=ids)
    return len(docs)


def query_collection(query_text: str, n: int = 5) -> list[dict]:
    coll = get_or_create_collection()
    res = coll.query(query_texts=[query_text], n_results=n)
    out = []
    for i, doc in enumerate(res["documents"][0]):
        out.append({
            "document": doc,
            "metadata": res["metadatas"][0][i],
            "distance": res["distances"][0][i],
        })
    return out


def stats() -> dict:
    coll = get_or_create_collection()
    n = coll.count()
    metadata = coll.metadata
    return {"name": COLLECTION_NAME, "count": n, "metadata": metadata}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Physis Finance Brain — 4지국 흡수 파이프라인")
    ap.add_argument("--create", action="store_true", help="컬렉션 생성/확인")
    ap.add_argument("--ingest-log", metavar="PATH", help="로그 파일 → 흡수")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--query", metavar="TEXT", help="자연어 쿼리")
    ap.add_argument("--stats", action="store_true", help="컬렉션 통계")
    args = ap.parse_args()

    if args.create:
        coll = get_or_create_collection()
        print(f"✅ 컬렉션 '{COLLECTION_NAME}' 준비 완료")
        print(f"   메타: {coll.metadata}")
        print(f"   현재 도큐먼트 수: {coll.count()}")

    if args.ingest_log:
        records = parse_pipeline_log(Path(args.ingest_log))
        print(f"파싱: {len(records)}건 결정 추출")
        n = ingest_records(records, date_label=args.date)
        print(f"흡수: {n}건 → {COLLECTION_NAME}")

    if args.query:
        results = query_collection(args.query)
        print(f"\n쿼리: {args.query}")
        print(f"결과 {len(results)}건:")
        for r in results:
            print(f"\n  거리={r['distance']:.3f}")
            print(f"  문서: {r['document']}")
            print(f"  메타: {r['metadata']}")

    if args.stats:
        s = stats()
        print(f"\n📊 {s['name']}")
        print(f"   카운트: {s['count']}")
        print(f"   메타: {s['metadata']}")
