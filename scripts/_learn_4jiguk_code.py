"""
4지국 STOCK 핵심 코드 모듈 흡수 — physis_finance_code 신규 컬렉션
2026-05-11 박제, 장 쉬는 동안 학습 사이클 가동.

방부장 명: "장이 쉬는동안 지수너는 최대한 학습을 많이 해놔라"
[[바람을_보다_비정형의_시선]] 1단계 — 정식으로 배운 학생.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv()

from scripts.embedding import GoogleEmbeddingClient, migrate_library
from scripts.setup_vector_db import ChromaDBIndex

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY 없음")
    sys.exit(1)

# 4지국 코드 전용 컬렉션
db = ChromaDBIndex(collection_name="physis_finance_code")
embedder = GoogleEmbeddingClient(api_key)

STOCK_ROOT = Path("/home/nas/STOCK-TRADING/Stock-Trading")
CODE_TARGETS = [
    # 의사결정 핵심 (멀티AI 앙상블)
    ("agents/ensemble_agent.py", "code_ensemble_가중투표_합의율"),
    ("agents/chart_agent.py", "code_chart_gemini_vision"),
    ("agents/screener_agent.py", "code_screener_ai_종목선정"),
    # 데이터 수집 (정형 도메인)
    ("data/news_scraper.py", "code_news_3중폴백_네이버연합"),
    ("data/dart_client.py", "code_dart_공시_재무"),
    ("data/chart_scraper.py", "code_chart_스크래핑"),
    ("data/stock_screener.py", "code_screener_KRX_급등주"),
    ("data/bio_event_scanner.py", "code_bio_이벤트_드리븐"),
    # 매크로 (시장 환경)
    ("data/macro/correlation_engine.py", "code_macro_상관관계엔진_자산배분"),
    ("data/macro/collector.py", "code_macro_yahoo_fred_수집"),
    ("data/macro/history_collector.py", "code_macro_이력_누적"),
    # 파이프라인 (오케스트레이션)
    ("scheduler/pipeline.py", "code_pipeline_전체흐름_HITL"),
    ("scheduler/macro_pipeline.py", "code_pipeline_macro"),
    ("scheduler/bio_pipeline.py", "code_pipeline_bio"),
    # 매매 실행
    ("api/kis_client.py", "code_kis_매매_안전캡"),
    # 전략 유틸
    ("utils/sector_phase.py", "code_util_섹터로테이션_4단계"),
    ("utils/signal_stocks.py", "code_util_시그널종목"),
]

print(f"=== 4지국 STOCK 핵심 코드 → physis_finance_code 흡수 ({len(CODE_TARGETS)} 파일) ===")
total = 0
fail = 0
for rel, cat in CODE_TARGETS:
    fp = STOCK_ROOT / rel
    if not fp.exists():
        print(f"❌ 누락: {rel}")
        fail += 1
        continue
    try:
        c = migrate_library(fp, cat, db, embedder)
        print(f"✅ {rel:50s} → {cat} ({c} 청크)")
        total += c
    except Exception as e:
        print(f"❌ {rel} 실패: {type(e).__name__}: {e}")
        fail += 1

print(f"\n=== 결과 ===")
print(f"총 {total} 청크 박제, {fail} 실패")
print(f"physis_finance_code 컬렉션: {db.collection.count()} 임베딩")
