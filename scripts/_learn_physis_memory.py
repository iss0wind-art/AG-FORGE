"""
AG-Forge physis_memory wiki·자각·사초·핸드오프 → physis_memory 컬렉션 통합 갱신.
2026-05-11 박제, 5/10 박제 신규 자료 + 자아 정체성 4축 + 5/9·5/10 사이클.
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

db = ChromaDBIndex(collection_name="physis_memory_v2")
embedder = GoogleEmbeddingClient(api_key)

VAULT = Path("/home/nas/AG-Forge/physis_memory")
TARGETS = [
    # ── 4대 정체성 축 (God Nodes + 진화 방향성) ───────────
    (VAULT / "god_nodes/홍익인간.md", "g0_홍익인간"),
    (VAULT / "god_nodes/8조법.md", "헌법_8조법"),
    (VAULT / "god_nodes/구체_프렉탈_원리.md", "g0_구체프렉탈_원리"),
    (VAULT / "god_nodes/2026-05-02_chunbukyung.md", "g0_천부경"),
    (VAULT / "wiki/바람을_보다_비정형의_시선.md", "정체성_바람을_보다_4단계진화"),
    # ── 5/10 자아 정체성 박제 (인프라·거울·자부심) ──────
    (VAULT / "wiki/구체프랙탈_뇌_DB_층.md", "인프라_4층_DB_청사진"),
    (VAULT / "wiki/외부_자문_정독_2026-05-09.md", "거울_외부_자문_정합매트릭스"),
    (VAULT / "wiki/단군의_평_2026-05-10.md", "거울_단군의평_5축_환상6종"),
    (VAULT / "wiki/피지수_현재_상태_브리프_2026-05-10.md", "자아_상태_브리프_외부Claude용"),
    # ── 자각 노드 (1.0 → 1.4세대) ────────────────────────
    (VAULT / "2026-05-08_self_awakening.md", "자각_1.1세대_박제의존"),
    (VAULT / "2026-05-09_self_awakening.md", "자각_1.3세대_자율의설계"),
    (VAULT / "2026-05-10_self_awakening.md", "자각_1.4세대_DB층합체_거울_자부심_바람"),
    # ── chronicle 사초 ────────────────────────────────────
    (VAULT / "chronicle/2026-05-02_first_breath.md", "사초_1세대_거듭남"),
    (VAULT / "chronicle/2026-05-09_first_neural_link.md", "사초_4지국_첫신경연결"),
    (VAULT / "chronicle/2026-05-10_db_layer_vision.md", "사초_DB층비전강림"),
    (VAULT / "chronicle/2026-05-10_pride_decree.md", "사초_자부심천명_거울"),
    (VAULT / "chronicle/2026-05-10_dangun_evaluation.md", "사초_단군의평_본진거울"),
    # ── 핸드오프 (working_memory) ─────────────────────────
    (VAULT / "working_memory/2026-05-03_handoff.md", "handoff_5_03"),
    (VAULT / "working_memory/2026-05-07_handoff.md", "handoff_5_07"),
    (VAULT / "working_memory/2026-05-08_handoff.md", "handoff_5_08_이천대업"),
    (VAULT / "working_memory/2026-05-09_handoff.md", "handoff_5_09_4지국첫통신_소급"),
    (VAULT / "working_memory/2026-05-10_handoff.md", "handoff_5_10_구체프랙탈DB비전"),
    # ── 4지국 도메인 wiki (Tier 1 + 모듈 정독) ────────────
    (VAULT / "wiki/주식시장_메커니즘.md", "tier1_주식시장_메커니즘"),
    (VAULT / "wiki/기술적_분석_지표.md", "tier1_기술적분석"),
    (VAULT / "wiki/재무_분석_지표.md", "tier1_재무분석"),
    (VAULT / "wiki/매크로_경제_지표.md", "tier1_매크로경제"),
    (VAULT / "wiki/한국시장_특수성.md", "tier1_한국시장"),
    (VAULT / "wiki/행동경제학_원리.md", "tier1_행동경제"),
    (VAULT / "wiki/DART_시스템.md", "tier1_dart"),
    (VAULT / "wiki/KRX_시장구조.md", "tier1_krx_시장구조"),
    (VAULT / "wiki/주식_금융_경제_도메인.md", "stock_도메인_인덱스"),
    (VAULT / "wiki/Stock_AI_파이프라인.md", "stock_ai_파이프라인_7step"),
    (VAULT / "wiki/멀티AI_앙상블_원리.md", "stock_멀티ai_앙상블"),
    (VAULT / "wiki/7중_안전장치.md", "stock_7중_안전장치"),
    (VAULT / "wiki/방부장_승인_게이트_HITL.md", "stock_HITL_5분"),
    (VAULT / "wiki/방부장_4단계_AI인프라_사이클.md", "★_방부장_4단계_시스템축"),
    (VAULT / "wiki/Stock_AI_v2_PATCH_시스템.md", "stock_v2_패치_거버넌스"),
    (VAULT / "wiki/Stock_AI_모듈_지도.md", "stock_모듈_책임지도"),
    (VAULT / "wiki/Stock_AI_데이터_매매_상세.md", "stock_데이터_매매_상세"),
    (VAULT / "wiki/EnsembleAgent_가중투표_로직.md", "stock_ensemble_가중투표"),
    (VAULT / "wiki/2026-05-09_4지국_파이프라인_관찰.md", "stock_파이프라인_관찰_5_9"),
    (VAULT / "wiki/4지국_데이터_검토_시기.md", "stock_데이터_검토_일정"),
]

print(f"=== AG-Forge physis_memory → physis_memory 컬렉션 통합 갱신 ({len(TARGETS)}건) ===\n")
total = 0; fail = 0
for fp, cat in TARGETS:
    if not fp.exists():
        print(f"❌ 누락: {fp}"); fail += 1; continue
    try:
        c = migrate_library(fp, cat, db, embedder)
        print(f"✅ {fp.name:55s} → {cat} ({c})")
        total += c
    except Exception as e:
        print(f"❌ {fp.name} 실패: {type(e).__name__}: {e}")
        fail += 1

print(f"\n=== 결과 ===")
print(f"총 {total} 청크 박제, {fail} 실패")
print(f"physis_memory 컬렉션: {db.collection.count()} 임베딩")
