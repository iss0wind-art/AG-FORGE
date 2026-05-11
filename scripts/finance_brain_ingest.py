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


def parse_jsonl_decisions(jsonl_path: Path) -> list[dict]:
    """4지국 logs/decisions/YYYY-MM-DD.jsonl 파싱 — 풍부한 결정 레코드 + PATCH 라인 병합.

    JSONL은 append-only라 base 라인 + 사후 PATCH 라인이 같은 id로 누적됨.
    여기서 id 기준 병합 → 1 결정 = 1 최종 레코드.
    피지수 학습 토양 (방부장 친명 2026-05-11 "4지국을 완벽하게 만들라").
    """
    if not jsonl_path.exists():
        return []
    merged: dict[str, dict] = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = rec.get("id")
        if not rid:
            continue
        if rec.get("patch"):
            if rid in merged:
                merged[rid].update({k: v for k, v in rec.items() if k != "patch"})
        else:
            merged[rid] = rec
    return list(merged.values())


def ingest_jsonl_records(records: list[dict], date_label: str | None = None) -> int:
    """JSONL 풍부 레코드 → physis_finance_brain. 모델별 raw + TV + 재무·차트·뉴스·HITL·체결·outcome 메타 전부 보존."""
    if date_label is None:
        date_label = datetime.now().strftime("%Y-%m-%d")
    coll = get_or_create_collection()
    docs, metas, ids = [], [], []
    for r in records:
        rid = r["id"]
        # 자연어 문서: 의미 검색 가능한 1줄 요약 (피지수 트래버설 진입점)
        signal = r.get("signal", "?")
        conf = r.get("confidence", 0.0) or 0.0
        agree = r.get("agreement_rate", 0.0) or 0.0
        gate = r.get("gate_result", "n/a")
        hitl = r.get("hitl_result", "n/a")
        executed = r.get("executed", None)
        outcome_score = r.get("outcome_score")
        doc_parts = [
            f"{r.get('stock_name','?')}({r.get('stock_code','?')})",
            f"signal={signal} conf={conf:.2f} agree={agree:.2f}",
            f"gate={gate} hitl={hitl}",
            f"sector={r.get('sector_tag','?')}/phase{r.get('sector_phase','?')}",
            f"tv_rec={r.get('tv_recommend_all', 'n/a')}",
            f"sentiment={r.get('market_sentiment','?')}",
        ]
        if executed is not None:
            doc_parts.append(f"executed={executed}")
        if outcome_score is not None:
            doc_parts.append(f"outcome_score={outcome_score}")
        reason = r.get("final", {}).get("reasoning") or r.get("selection_reason") or ""
        if reason:
            doc_parts.append(f"reasoning={reason[:200]}")
        doc = " | ".join(doc_parts)

        # 메타: ChromaDB가 검색 가능한 scalar 값들 (str/float/int/bool 만 허용)
        def _scalar(v, default=""):
            if v is None:
                return default
            if isinstance(v, (str, int, float, bool)):
                return v
            return str(v)[:500]

        meta = {
            "date": date_label,
            "decision_id": rid,
            "stock_code": _scalar(r.get("stock_code"), ""),
            "stock_name": _scalar(r.get("stock_name"), ""),
            "signal": _scalar(r.get("signal"), "?"),
            "confidence": float(r.get("confidence") or 0.0),
            "agreement_rate": float(r.get("agreement_rate") or 0.0),
            "gate_result": _scalar(r.get("gate_result"), "n/a"),
            "hitl_result": _scalar(r.get("hitl_result"), "n/a"),
            "executed": bool(r.get("executed", False)),
            "market_sentiment": _scalar(r.get("market_sentiment"), "중립"),
            "sector_phase": _scalar(r.get("sector_phase"), ""),
            "sector_tag": _scalar(r.get("sector_tag"), ""),
            "phase_weight": float(r.get("phase_weight") or 1.0),
            "tv_recommend_all": float(r.get("tv_recommend_all") or 0.0) if r.get("tv_recommend_all") is not None else 0.0,
            "price_at_decision": int(r.get("price_at_decision") or 0),
            "outcome_score": float(r.get("outcome_score") or 0.0) if r.get("outcome_score") is not None else 0.0,
            "kis_mode": _scalar(r.get("kis_mode"), ""),
            "source": "jiguk4_jsonl",
        }
        docs.append(doc)
        metas.append(meta)
        ids.append(f"jsonl_{rid}")

    if docs:
        coll.upsert(documents=docs, metadatas=metas, ids=ids)
    return len(docs)


def ingest_jsonl_file(jsonl_path: str | Path, date_label: str | None = None) -> int:
    """외부 호출용 단축 함수 — pipeline.py 종료 시 import 해서 호출."""
    records = parse_jsonl_decisions(Path(jsonl_path))
    return ingest_jsonl_records(records, date_label=date_label)


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
        # PATCH 2026-05-11: coll.add → coll.upsert. ID 동일 시 덮어씀 → cron 매일 가동 시 dedupe.
        coll.upsert(documents=docs, metadatas=metas, ids=ids)
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
    ap.add_argument("--ingest-jsonl", metavar="PATH", help="4지국 풍부 결정 JSONL → 흡수")
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

    if args.ingest_jsonl:
        records = parse_jsonl_decisions(Path(args.ingest_jsonl))
        print(f"파싱(JSONL): {len(records)}건 풍부 결정 추출")
        n = ingest_jsonl_records(records, date_label=args.date)
        print(f"흡수(JSONL): {n}건 → {COLLECTION_NAME}")

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
