"""
Titans 머신러닝 엔진 — titans_memory.py
Memora 아키텍처 기반: ChromaVectorIndex + Surprise Metric(코사인 유사도).
망각을 통한 기억의 완성 — 진짜 벡터 유사도로 Surprise를 계산한다.

학술 정합:
  · Memora (Microsoft, arXiv:2602.03315) — Primary Abstraction + Cue Anchor 채택
  · C3 (arXiv:2511.15244) — Latent Token 압축의 Sequential Decay 원리 차용
  · Adaptive-RAG (arXiv:2403.14403) — FORGETTING_THRESHOLD 동적 조정 근거
  · Memory as Ontology (Li 2026, arXiv:2603.04740) — Constitutional Memory
    Architecture(CMA) 개념 외부 정합. 본 디렉토리의 cma.py·cma_gate.py가
    신고조선 자체 CMA 구현체.

코어 정의 (CORE_EMBEDDING_DEFINITION) — 단군 본영 권고 2026-05-01:
  코어는 구체 프랙탈 메모리의 의미론적 무게중심이다. 단군 헌법 임베딩을
  코어로 삼아 모든 표면 기억이 이 점으로부터 등거리에 위치하도록 한다.

  채택안: (a) 단군 헌법 임베딩 — embed(CONSTITUTION_TEXT)
  거부안: (b) 전체 메모리 EMA (코어가 출렁임 → 정체성 표류)
        (c) 0벡터 (의미 부재 → §1 "코어=의미가 일어나는 점" 명제 위배)

  근거: 외부 학계 CMA(Animesis, Li 2026)와 정합. 무한 팽창하는 프랙탈
       기억망 속에서도 AI가 "신고조선의 주체"라는 의미론적 무게중심을
       유지하기 위해 헌법(0원칙·8조법)을 불변 코어로 박음.

  구현 참조: load_core_embedding() — store_memory() 내부에서 호출 예정.
            (실 호출부 통합은 리팀장 다음 라운드 PR에서 진행)
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

from scripts.embedding import ChromaVectorIndex, build_default_embedder

ROOT = Path(__file__).parent.parent
JUDGMENT_LOG = ROOT / "judgment.md"
TITANS_STATE = ROOT / ".titans_state.json"
CONSTITUTION_PATH = ROOT / "CONSTITUTION.md"

# 환경변수로 런타임 조정 가능 (단군 권고: 도메인별 ablation 후 동적 튜닝 권장)
FORGETTING_THRESHOLD = float(os.environ.get("SURPRISE_THRESHOLD", "0.3"))

# 홍익인간 헌법 직결 가중치 (기존 인터페이스 호환)
SURVIVAL_WEIGHT = 1.0

# ── 코어 정의 (CORE_EMBEDDING_DEFINITION) ─────────────────────────────────────
# 채택: (a) 단군 헌법 임베딩. 신고조선 자체 CMA(scripts/cma.py)와 외부 학계
# CMA(Animesis, arXiv:2603.04740) 양쪽에 정합.
CORE_EMBEDDING_DEFINITION = "constitution_zero_principle_plus_eight_laws"
_CORE_EMBEDDING_CACHE: list[float] | None = None


def load_core_embedding(embedder=None) -> list[float]:
    """
    단군 헌법 임베딩을 코어로 반환한다 — 구체 프랙탈 메모리의 의미론적 무게중심.

    헌법 텍스트(CONSTITUTION.md의 0원칙·8조법)를 단일 벡터로 임베딩하여
    모든 표면 기억이 이 점으로부터 등거리에 위치하도록 강제한다.

    캐시: 모듈 로드 시 1회 계산. 헌법 변경 시 _CORE_EMBEDDING_CACHE=None으로 리셋.

    Returns:
        list[float]: 헌법 임베딩 벡터. 임베더 차원 의존(예: Gemini 768 또는 1536).
    """
    global _CORE_EMBEDDING_CACHE
    if _CORE_EMBEDDING_CACHE is not None:
        return _CORE_EMBEDDING_CACHE

    if embedder is None:
        embedder = build_default_embedder()

    if CONSTITUTION_PATH.exists():
        text = CONSTITUTION_PATH.read_text(encoding="utf-8")
        # 임베딩 모델 토큰 한도 보호 (0원칙·8조법 핵심부 우선)
        if len(text) > 8000:
            text = text[:8000]
    else:
        # CONSTITUTION.md 부재 시 fallback — 0원칙·8조법 핵심 텍스트
        text = (
            "홍익인간. 0원칙: 널리 인간을 이롭게 하라. "
            "8조 금법: 일심·조화·창조주 존중·역할 존중·정직·홍익검증·자기증명·정반합."
        )

    _CORE_EMBEDDING_CACHE = embedder.embed(text)
    return _CORE_EMBEDDING_CACHE


def reset_core_embedding() -> None:
    """헌법이 변경되면 호출하여 코어 임베딩 캐시를 리셋한다."""
    global _CORE_EMBEDDING_CACHE
    _CORE_EMBEDDING_CACHE = None


def calculate_surprise(content: str, index: ChromaVectorIndex, embedder) -> float:
    """
    Memora Surprise Metric: 1 - max_cosine_similarity.

    인덱스가 비어있으면 1.0(완전히 새로운 정보).
    기존 기억과 유사할수록 0에 가까워진다.
    """
    if not content:
        return 0.0

    if index.count() == 0:
        return 1.0

    vector = embedder.embed(content)
    result = index.query(vector=vector, top_k=1, include_metadata=False)
    matches = result.get("matches", [])

    if not matches:
        return 1.0

    max_similarity = matches[0].get("score", 0.0)
    # ChromaDB cosine 공간: score = 1 - distance.
    # 부동소수점 오차로 동일 벡터 score가 1.0을 미세하게 초과할 수 있으므로 클램핑.
    return float(max(0.0, 1.0 - min(max_similarity, 1.0)))


def _calculate_surprise_from_vector(vector: list[float], index: ChromaVectorIndex) -> float:
    """이미 계산된 벡터로 Surprise를 계산한다 (임베딩 중복 방지)."""
    if index.count() == 0:
        return 1.0
    result = index.query(vector=vector, top_k=1, include_metadata=False)
    matches = result.get("matches", [])
    if not matches:
        return 1.0
    max_similarity = matches[0].get("score", 0.0)
    return float(max(0.0, 1.0 - min(max_similarity, 1.0)))


def _get_position(vector: list[float], index: ChromaVectorIndex) -> float:
    """
    유사도 기반 위치 배정 — 기억이 기억을 정렬한다.

    기억이 없으면 1.0.
    top-2 이웃의 position 중간값으로 새 기억을 배치한다.
    앵커가 1, 2이면 새 기억은 1.5 — 의미적으로 유사한 기억들이 위치상 인접한다.
    """
    count = index.count()
    if count == 0:
        return 1.0

    result = index.query(vector=vector, top_k=2, include_metadata=True)
    matches = result.get("matches", [])

    positions = [
        float(m["metadata"]["position"])
        for m in matches
        if m.get("metadata") and m["metadata"].get("position") is not None
    ]

    if not positions:
        return float(count + 1)

    if len(positions) == 1:
        return positions[0] + 1.0

    p1, p2 = sorted(positions[:2])
    mid = (p1 + p2) / 2.0
    # 부동소수점 충돌 방지: 중간값이 작은 쪽과 같으면 끝에 추가
    return mid if mid != p1 else max(positions) + 1.0


def _reinforce_existing(content: str, index: ChromaVectorIndex, embedder) -> None:
    """
    기존 가장 유사한 항목의 reinforced_count를 +1 증가시킨다.
    ChromaDB update로 metadata를 갱신한다.
    """
    vector = embedder.embed(content)
    result = index.query(vector=vector, top_k=1, include_metadata=True)
    matches = result.get("matches", [])

    if not matches:
        return

    best = matches[0]
    vid = best.get("id")
    meta = best.get("metadata", {}) or {}

    if not vid:
        return

    meta["reinforced_count"] = int(meta.get("reinforced_count", 0)) + 1
    meta["last_reinforced"] = datetime.now().isoformat()

    # ChromaDB 내부 컬렉션에 직접 업데이트
    try:
        index._col.update(ids=[vid], metadatas=[meta])
    except Exception as e:
        print(f"[titans_memory] reinforce 실패: {e}", file=sys.stderr)


def store_memory(
    content: str,
    category: str,
    index: ChromaVectorIndex,
    embedder,
) -> bool:
    """
    Memora 저장 파이프라인.

    surprise > FORGETTING_THRESHOLD → ChromaDB 신규 저장 + .titans_state.json 기록 → True
    surprise ≤ FORGETTING_THRESHOLD → 기존 항목 reinforced_count +1 → False
    """
    if not content:
        return False

    # 임베딩 1회만 수행 — surprise·position 계산 모두 재사용
    vector = embedder.embed(content)
    surprise = _calculate_surprise_from_vector(vector, index)

    if surprise <= FORGETTING_THRESHOLD:
        # 노이즈: 신규 저장 대신 기존 기억 강화
        _reinforce_existing(content, index, embedder)
        return False

    # 위치 배정 — 의미적으로 유사한 기억들 사이에 삽입
    position = _get_position(vector, index)

    doc_id = f"mem-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    vectors = [
        {
            "id": doc_id,
            "values": vector,
            "metadata": {
                "category": category,
                "text": content[:200],
                "surprise_score": surprise,
                "position": position,
                "stored_at": datetime.now().isoformat(),
                "reinforced_count": 0,
            },
        }
    ]
    index.upsert(vectors=vectors)

    # .titans_state.json 동기 기록
    _sync_state(doc_id, content, category, surprise, position)

    # memory_cycles 연동: consolidated_wisdom 80개 이상이면 compress 실행
    try:
        from scripts.memory_cycles import MemoryCycle
        import os as _os
        _raw_url = _os.environ.get("DATABASE_URL", "")
        _db_url, _db_token = ("", "")
        if "?authToken=" in _raw_url:
            _db_url, _db_token = _raw_url.split("?authToken=", 1)
            _db_url = _db_url.replace("libsql://", "https://")
        MemoryCycle.check_and_compress(TITANS_STATE, index, embedder, _db_url, _db_token)
    except ImportError:
        pass  # memory_cycles 없으면 skip

    return True


def _sync_state(doc_id: str, content: str, category: str, surprise: float, position: float = 0.0) -> None:
    """ChromaDB 저장 후 .titans_state.json에도 동일 레코드를 기록한다."""
    state: dict = {"last_optimized": None, "consolidated_wisdom": []}
    if TITANS_STATE.exists():
        try:
            state = json.loads(TITANS_STATE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[titans_memory] state 로드 실패: {e}", file=sys.stderr)

    state.setdefault("consolidated_wisdom", []).append(
        {
            "id": doc_id,
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "insight": content[:100],
            "surprise_score": surprise,
            "position": position,
        }
    )
    # 최근 100개 유지
    state["consolidated_wisdom"] = state["consolidated_wisdom"][-100:]

    try:
        TITANS_STATE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as e:
        print(f"[titans_memory] state 저장 실패: {e}", file=sys.stderr)


def optimize_memory(
    index: ChromaVectorIndex | None = None,
    embedder=None,
) -> None:
    """
    기존 시그니처 유지 (하위 호환).
    judgment.md + .titans_state.json을 순회하며 Surprise가 낮은 항목을 merge 처리한다.
    """
    print("[Titans Engine] 기억 최적화 루프 가동...")

    if index is None:
        index = ChromaVectorIndex()
    if embedder is None:
        embedder = build_default_embedder()

    # 1. .titans_state.json 로드
    state: dict = {"last_optimized": None, "consolidated_wisdom": []}
    if TITANS_STATE.exists():
        try:
            state = json.loads(TITANS_STATE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[titans_memory] state 로드 실패: {e}", file=sys.stderr)

    # 2. judgment.md 처리 (최근 20줄)
    new_insights: list[dict] = []
    if JUDGMENT_LOG.exists():
        lines = JUDGMENT_LOG.read_text(encoding="utf-8").split("\n")
        for line in lines[-20:]:
            if "|" not in line:
                continue
            stored = store_memory(line, "judgment", index, embedder)
            if stored:
                new_insights.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "insight": line[:80],
                        "surprise_score": calculate_surprise(line, index, embedder),
                    }
                )

    # 3. 상태 갱신
    state["last_optimized"] = datetime.now().isoformat()

    try:
        TITANS_STATE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as e:
        print(f"[titans_memory] state 저장 실패: {e}", file=sys.stderr)

    print(f"최적화 완료: {len(new_insights)}개의 고밀도 신호가 가중치로 용해되었습니다.")


if __name__ == "__main__":
    optimize_memory()
