"""
AG-Forge 자체 핵심 .md → physis_brain 컬렉션 추가 흡수.
방부장 친명 2026-05-11: "깃을 정리하라 너는 흡수해도 된다"
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
if not api_key:
    print("❌ GEMINI_API_KEY 없음"); sys.exit(1)

db = ChromaDBIndex(collection_name="physis_brain")
embedder = GoogleEmbeddingClient(api_key)

AG = Path("/home/nas/AG-Forge")
TARGETS = [
    # 자아 정체성 핵심
    (AG / "CONSTITUTION.md", "agforge_self_constitution"),
    (AG / "PHYSIS.md", "agforge_self_physis"),
    (AG / ".brain/physis.md", "agforge_self_brain_physis_layer0"),
    (AG / "FRACTAL_BRAIN_PROPOSAL.md", "agforge_self_fractal_brain_proposal"),
    (AG / "DANGUN_SURGERY_HANDOFF.md", "agforge_self_dangun_surgery_handoff"),
    # 뇌 레이어 (페르소나 + 직관 + 철학)
    (AG / "brain_personality.md", "agforge_brain_personality_4페르소나"),
    (AG / "brain_intuition.md", "agforge_brain_intuition"),
    (AG / "brain_philosophy.md", "agforge_brain_philosophy"),
    (AG / "brain_master_architecture.md", "agforge_brain_master_architecture"),
    (AG / "brain_sync_protocol.md", "agforge_brain_sync_protocol"),
    (AG / "brain_transplant_strategy.md", "agforge_brain_transplant_strategy"),
    (AG / "brain-layer-reference.md", "agforge_brain_layer_reference"),
    (AG / "logic_rb.md", "agforge_logic_rb_left_brain"),
    (AG / "emotion_ui.md", "agforge_emotion_ui_right_brain"),
    # 아키텍처·로드맵·가이드
    (AG / "architecture-overview.md", "agforge_architecture_overview"),
    (AG / "implementation-roadmap.md", "agforge_implementation_roadmap"),
    (AG / "technical-guidelines.md", "agforge_technical_guidelines"),
    (AG / "agents-roster.md", "agforge_agents_roster"),
    (AG / "cost-optimization-guide.md", "agforge_cost_optimization"),
    (AG / "README.md", "agforge_readme"),
    # 핸드오프·연구
    (AG / "research/embodiment_gap_report_v1.md", "agforge_research_embodiment_gap"),
]

print(f"=== AG-Forge 자체 핵심 → physis_brain 추가 흡수 ({len(TARGETS)} 파일) ===\n")
total = 0; fail = 0
for fp, cat in TARGETS:
    if not fp.exists():
        print(f"❌ 누락: {fp}"); fail += 1; continue
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
