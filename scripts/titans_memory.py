"""
Titans 머신러닝 엔진 — titans_memory.py
Memora 아키텍처 기반: ChromaVectorIndex + Surprise Metric(코사인 유사도).
망각을 통한 기억의 완성 — 진짜 벡터 유사도로 Surprise를 계산한다.
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

# 환경변수로 런타임 조정 가능
FORGETTING_THRESHOLD = float(os.environ.get("SURPRISE_THRESHOLD", "0.3"))

# 홍익인간 헌법 직결 가중치 (기존 인터페이스 호환)
SURVIVAL_WEIGHT = 1.0


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
    surprise = calculate_surprise(content, index, embedder)

    if surprise <= FORGETTING_THRESHOLD:
        # 노이즈: 신규 저장 대신 기존 기억 강화
        _reinforce_existing(content, index, embedder)
        return False

    # 신규 저장
    vector = embedder.embed(content)
    doc_id = f"mem-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    vectors = [
        {
            "id": doc_id,
            "values": vector,
            "metadata": {
                "category": category,
                "text": content[:200],
                "surprise_score": surprise,
                "stored_at": datetime.now().isoformat(),
                "reinforced_count": 0,
            },
        }
    ]
    index.upsert(vectors=vectors)

    # .titans_state.json 동기 기록
    _sync_state(doc_id, content, category, surprise)

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


def _sync_state(doc_id: str, content: str, category: str, surprise: float) -> None:
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
