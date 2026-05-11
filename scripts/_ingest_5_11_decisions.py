"""
5/11 4지국 거래 결정 4건 수동 박제 — 학습 손실 회복.
방부장 명: "권장한대로 진행해" (A+B 자율 진행)

HITL 메시지 기반 추출 — physis_finance_brain 컬렉션에 박제.
ChromaDB 기본 임베딩(MiniLM 384차원) 호환.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.finance_brain_ingest import get_or_create_collection, _finalize, ingest_records


# 5/11 12:10대 HITL 메시지에서 추출한 4건 (방부장 승인 완료)
DECISIONS_5_11 = [
    {
        "pipeline_start": "12:10",
        "stock_name": "TIGER 반도체TOP10",
        "stock_code": "396500",
        "market_sentiment": "중립",  # 메시지에 명시 없음, 매크로 국면 '정상'에서 보수적 추정
        "signal_time": "12:10:13",
        "signal": "SELL",
        "confidence": 0.81,
        "agreement_rate": 0.0,  # 메시지에 합의율 미명시, 0으로 (게이트 통과했으니 60% 이상 추정)
        "gate_passed": True,
        "hitl_result": "approved",
        "hitl_decided_at": "12:10:20",
    },
    {
        "pipeline_start": "12:10",
        "stock_name": "KODEX 2차전지산업레버리지",
        "stock_code": "462330",
        "market_sentiment": "중립",
        "signal_time": "12:10:38",
        "signal": "BUY",
        "confidence": 0.74,
        "agreement_rate": 0.0,
        "gate_passed": True,
        "hitl_result": "approved",
        "hitl_decided_at": "12:10:44",
    },
    {
        "pipeline_start": "12:10",
        "stock_name": "한온시스템",
        "stock_code": "018880",
        "market_sentiment": "중립",
        "signal_time": "12:11:07",
        "signal": "BUY",
        "confidence": 0.76,
        "agreement_rate": 0.0,
        "gate_passed": True,
        "hitl_result": "approved",
        "hitl_decided_at": "12:11:13",
    },
    {
        "pipeline_start": "12:10",
        "stock_name": "진원생명과학",
        "stock_code": "011000",
        "market_sentiment": "중립",
        "signal_time": "12:11:35",
        "signal": "SELL",
        "confidence": 0.88,
        "agreement_rate": 0.0,
        "gate_passed": True,
        "hitl_result": "approved",
        "hitl_decided_at": "12:11:43",
    },
]


if __name__ == "__main__":
    finalized = [_finalize(d) for d in DECISIONS_5_11]
    print(f"=== 5/11 거래 결정 4건 수동 박제 (학습 손실 회복) ===\n")
    for d in finalized:
        print(f"  [{d['signal_time']}] {d['stock_name']}({d['stock_code']}) {d['signal']} "
              f"신뢰도 {d['confidence']:.0%} → {d['hitl_result']}")
    n = ingest_records(finalized, date_label="2026-05-11")
    coll = get_or_create_collection()
    print(f"\n✅ {n}건 박제 완료. physis_finance_brain 컬렉션: {coll.count()} 임베딩 (5/9 30 + 5/11 4 + 메타1 = 35)")
