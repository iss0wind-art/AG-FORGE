"""
4지국 STOCK-TRADING 핵심 .md 흡수 — physis_finance_docs 컬렉션 추가 학습
2026-05-10 박제, 내일 장 본격 테스트 직전 학습 사이클.
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

# physis_finance_docs 컬렉션에 박제
db = ChromaDBIndex(collection_name="physis_finance_docs")
embedder = GoogleEmbeddingClient(api_key)

STOCK_ROOT = Path("/home/nas/STOCK-TRADING/Stock-Trading")
TARGETS = [
    (STOCK_ROOT / "README.md", "stock_pipeline_overview"),
    (STOCK_ROOT / "Assumption.md", "stock_assumption_facts_risks"),
    (STOCK_ROOT / "docs/decisions/2026-05-09-v2-direction.md", "stock_v2_direction_decision"),
    (STOCK_ROOT / "docs/PATCHES.md", "stock_patches_dr_sr_op"),
    (STOCK_ROOT / "docs/NAS_QUICKSTART.md", "stock_nas_deploy_quickstart"),
    (STOCK_ROOT / "docs/MCP_SETUP.md", "stock_mcp_setup"),
    (STOCK_ROOT / "docs/DEPLOY_NAS.md", "stock_deploy_nas"),
]

print(f"=== 4지국 STOCK-TRADING 핵심 자료 → physis_finance_docs 흡수 ({len(TARGETS)}건) ===")
total = 0
for fp, cat in TARGETS:
    if not fp.exists():
        print(f"❌ 누락: {fp}")
        continue
    try:
        c = migrate_library(fp, cat, db, embedder)
        print(f"✅ {fp.name} → {cat} ({c} 청크)")
        total += c
    except Exception as e:
        print(f"❌ {fp.name} 실패: {type(e).__name__}: {e}")

print(f"\n총 {total} 청크 박제 완료. physis_finance_docs 컬렉션 갱신.")
print(f"컬렉션 현재 크기: {db.collection.count()} 임베딩")
