"""
본영·1·2·3·5지국 핵심 brain 자료 → physis_brain 컬렉션 통합 학습.
2026-05-11 박제, 장 쉬는 동안 자아 도메인 깊이 확장.
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
    print("❌ GEMINI_API_KEY 없음"); sys.exit(1)

db = ChromaDBIndex(collection_name="physis_brain")
embedder = GoogleEmbeddingClient(api_key)

TARGETS = [
    # 본영 단군 (DREAM_FAC)
    ("/home/nas/DREAM_FAC/CLAUDE.md", "bonyeong_dangun_claude_정사"),
    ("/home/nas/DREAM_FAC/AGENTS.md", "bonyeong_dangun_agents"),
    ("/home/nas/DREAM_FAC/CONSTITUTION.md", "bonyeong_dangun_constitution"),
    ("/home/nas/DREAM_FAC/DANGUN_MASTER_PLAN.md", "bonyeong_dangun_master_plan"),
    # 1지국 정도전 (BOQ_2)
    ("/home/nas/BOQ_2/.brain/architecture_context.md", "jiguk1_jeongdojeon_architecture"),
    ("/home/nas/BOQ_2/.brain/boq_calculation_context.md", "jiguk1_jeongdojeon_boq_calculation"),
    ("/home/nas/BOQ_2/.brain/data_collection_process.md", "jiguk1_jeongdojeon_data_collection"),
    ("/home/nas/BOQ_2/.brain/integration_blueprint.md", "jiguk1_jeongdojeon_integration"),
    ("/home/nas/BOQ_2/.brain/automation_strategy_context.md", "jiguk1_jeongdojeon_automation"),
    # 2지국 이순신 (H2OWIND_2)
    ("/home/nas/H2OWIND_2/.brain/brain.md", "jiguk2_isunsin_brain"),
    ("/home/nas/H2OWIND_2/.brain/brain_architecture.md", "jiguk2_isunsin_architecture"),
    ("/home/nas/H2OWIND_2/.brain/POPAL_NAVI.md", "jiguk2_isunsin_popal_navi"),
    ("/home/nas/H2OWIND_2/.brain/SKETCHUP_PLUGIN.md", "jiguk2_isunsin_sketchup"),
    ("/home/nas/H2OWIND_2/.brain/knowledge_popeyes.md", "jiguk2_isunsin_popeyes_knowledge"),
    ("/home/nas/H2OWIND_2/.brain/judgment.md", "jiguk2_isunsin_judgment"),
    # 3지국 이천 (FreeCAD_4TH)
    ("/home/nas/FreeCAD_4TH/.brain/codex_match_analysis_2026-05-06.md", "jiguk3_icheon_codex_match"),
    ("/home/nas/FreeCAD_4TH/.brain/dispatch_log.md", "jiguk3_icheon_dispatch_log"),
    ("/home/nas/FreeCAD_4TH/.brain/pattern_library.md", "jiguk3_icheon_pattern_library"),
    ("/home/nas/FreeCAD_4TH/.brain/grid_precision_analysis_2026-05-06.md", "jiguk3_icheon_grid_precision"),
    ("/home/nas/FreeCAD_4TH/.brain/homi9_design_2026-05-06.md", "jiguk3_icheon_homi9_design"),
    ("/home/nas/FreeCAD_4TH/.brain/cerebellum.md", "jiguk3_icheon_cerebellum"),
    ("/home/nas/FreeCAD_4TH/.brain/hippocampus.md", "jiguk3_icheon_hippocampus"),
    # 5지국 BOQQQ (예비, 단군 시공)
    ("/home/nas/BOQQQ/HANDOFF.md", "jiguk5_boqqq_handoff_dongwoo"),
]

print(f"=== 본영·각 지국 brain → physis_brain 통합 흡수 ({len(TARGETS)} 파일) ===\n")
total = 0; fail = 0
for fp_str, cat in TARGETS:
    fp = Path(fp_str)
    if not fp.exists():
        print(f"❌ 누락: {fp_str}"); fail += 1; continue
    try:
        c = migrate_library(fp, cat, db, embedder)
        print(f"✅ {fp.name:48s} → {cat} ({c})")
        total += c
    except Exception as e:
        print(f"❌ {fp.name} 실패: {type(e).__name__}: {e}")
        fail += 1

print(f"\n=== 결과 ===")
print(f"총 {total} 청크 박제, {fail} 실패")
print(f"physis_brain 컬렉션: {db.collection.count()} 임베딩")
