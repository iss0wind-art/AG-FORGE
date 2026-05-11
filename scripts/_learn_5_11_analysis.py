"""
5/11 장중 분석 wiki 노드 → ChromaDB physis_finance_docs 흡수.
방부장 명: "학습하고 적재하라" + "트레이딩 뷰에서 긁어올수있는 자료있으면 더 가져와"
"""
import os, sys
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv()
from scripts.embedding import GoogleEmbeddingClient, migrate_library
from scripts.setup_vector_db import ChromaDBIndex

api_key = os.environ.get("GEMINI_API_KEY")
db = ChromaDBIndex(collection_name="physis_finance_docs")
embedder = GoogleEmbeddingClient(api_key)

TARGETS = [
    (ROOT / "physis_memory/wiki/5_11_장중_거래결정_37건_정독.md", "5_11_장중_분석_outcome_seed"),
    (ROOT / "physis_memory/wiki/TradingView_시범가동_정합검증_2026-05-11.md", "TV_시범가동_검증"),
    (ROOT / "physis_memory/wiki/그날의_비전_중심점_공명_직관.md", "그날의_비전_종결좌표"),
    (ROOT / "physis_memory/chronicle/2026-05-11_failure_as_seed.md", "사초_실패의_동력"),
]

print(f"=== 5/11 분석 wiki → physis_finance_docs 흡수 ({len(TARGETS)}건) ===\n")
total = 0
for fp, cat in TARGETS:
    if not fp.exists():
        print(f"❌ 누락: {fp}"); continue
    try:
        c = migrate_library(fp, cat, db, embedder)
        print(f"✅ {fp.name:45s} → {cat} ({c} 청크)")
        total += c
    except Exception as e:
        print(f"❌ {fp.name}: {e}")

print(f"\n총 {total} 청크 박제, physis_finance_docs: {db.collection.count()} 임베딩")
