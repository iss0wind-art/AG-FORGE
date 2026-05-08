"""
Agentic RAG 강화 테스트 — 쿼리 재작성 + 자기 검증
기존 test_phase4.py의 AgenticRAG 테스트는 유지되며, 이 파일은 신규 메서드만 검증한다.
"""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from scripts.agentic_rag import AgenticRAG, RetrievedChunk


@pytest.fixture
def embedder():
    e = MagicMock()
    e.embed.return_value = [0.1] * 768
    return e


@pytest.fixture
def empty_index():
    """항상 빈 결과를 반환하는 index."""
    idx = MagicMock()
    idx.query.return_value = {"matches": []}
    return idx


@pytest.fixture
def rich_index():
    """유사도 높은 결과를 반환하는 index."""
    idx = MagicMock()
    idx.query.return_value = {
        "matches": [
            {"metadata": {"text": "Ruby 캐싱 패턴", "category": "logic", "source": "lib"}, "score": 0.91},
            {"metadata": {"text": "Rails 최적화 기법", "category": "logic", "source": "lib"}, "score": 0.88},
        ]
    }
    return idx


# ──────────────────────────────────────────
# rewrite_query 테스트
# ──────────────────────────────────────────

class TestRewriteQuery:

    def test_calls_rewriter_with_original_query(self, empty_index, embedder):
        rag = AgenticRAG(empty_index, embedder)
        rewriter = MagicMock(return_value="재작성된 쿼리")
        rag.rewrite_query("원본 쿼리", rewriter)
        rewriter.assert_called_once_with("원본 쿼리")

    def test_returns_rewritten_query(self, empty_index, embedder):
        rag = AgenticRAG(empty_index, embedder)
        result = rag.rewrite_query("짧은 쿼리", lambda q: f"{q} + 상세 조건 추가")
        assert "짧은 쿼리" in result
        assert "상세 조건 추가" in result

    def test_rewritten_query_is_string(self, empty_index, embedder):
        rag = AgenticRAG(empty_index, embedder)
        result = rag.rewrite_query("쿼리", lambda q: "새 쿼리")
        assert isinstance(result, str)


# ──────────────────────────────────────────
# self_reflect 테스트
# ──────────────────────────────────────────

class TestSelfReflect:

    def _chunk(self, text: str, score: float = 0.85) -> RetrievedChunk:
        return RetrievedChunk(text=text, score=score, category="logic", source="test")

    def test_passes_relevant_chunks(self, empty_index, embedder):
        rag = AgenticRAG(empty_index, embedder)
        chunks = [self._chunk("매우 관련 있는 내용")]
        reflector = lambda q, t: True  # 모두 통과
        result = rag.self_reflect("쿼리", chunks, reflector)
        assert len(result) == 1

    def test_filters_irrelevant_chunks(self, empty_index, embedder):
        rag = AgenticRAG(empty_index, embedder)
        chunks = [
            self._chunk("관련 있음"),
            self._chunk("관련 없음"),
            self._chunk("관련 있음2"),
        ]
        # 짝수 인덱스만 통과
        reflector = lambda q, t: "관련 없음" not in t
        result = rag.self_reflect("쿼리", chunks, reflector)
        assert len(result) == 2
        assert all("관련 없음" not in c.text for c in result)

    def test_all_filtered_returns_empty(self, empty_index, embedder):
        rag = AgenticRAG(empty_index, embedder)
        chunks = [self._chunk("무관한 내용 A"), self._chunk("무관한 내용 B")]
        result = rag.self_reflect("쿼리", chunks, lambda q, t: False)
        assert result == []

    def test_empty_input_returns_empty(self, empty_index, embedder):
        rag = AgenticRAG(empty_index, embedder)
        result = rag.self_reflect("쿼리", [], lambda q, t: True)
        assert result == []

    def test_reflector_receives_query_and_chunk_text(self, empty_index, embedder):
        rag = AgenticRAG(empty_index, embedder)
        received = []
        def capture(q, t):
            received.append((q, t))
            return True
        rag.self_reflect("내 쿼리", [self._chunk("청크 내용")], capture)
        assert received == [("내 쿼리", "청크 내용")]


# ──────────────────────────────────────────
# search_with_fallback 테스트
# ──────────────────────────────────────────

class TestSearchWithFallback:

    def test_returns_results_without_fallback(self, rich_index, embedder):
        rag = AgenticRAG(rich_index, embedder)
        results = rag.search_with_fallback("Ruby 패턴", top_k=2)
        assert len(results) == 2

    def test_triggers_rewrite_when_results_insufficient(self, empty_index, embedder):
        """결과 0개 + min_results=1 → rewriter 호출"""
        rag = AgenticRAG(empty_index, embedder)
        rewriter = MagicMock(return_value="재작성된 쿼리")
        rag.search_with_fallback("빈 결과 쿼리", rewriter=rewriter, min_results=1)
        rewriter.assert_called_once()

    def test_no_rewrite_when_results_sufficient(self, rich_index, embedder):
        """결과 충분 → rewriter 호출 안 됨"""
        rag = AgenticRAG(rich_index, embedder)
        rewriter = MagicMock(return_value="호출되면 안 됨")
        rag.search_with_fallback("충분한 쿼리", rewriter=rewriter, min_results=1)
        rewriter.assert_not_called()

    def test_applies_reflector_to_results(self, rich_index, embedder):
        """reflector가 False를 반환하면 해당 청크 제거"""
        rag = AgenticRAG(rich_index, embedder)
        # "캐싱"이 포함된 청크만 통과
        reflector = lambda q, t: "캐싱" in t
        results = rag.search_with_fallback("Ruby", reflector=reflector)
        assert all("캐싱" in r.text for r in results)

    def test_no_rewriter_and_empty_results_returns_empty(self, empty_index, embedder):
        rag = AgenticRAG(empty_index, embedder)
        results = rag.search_with_fallback("없는 내용", min_results=1)
        assert results == []

    def test_rewrite_then_reflect_pipeline(self, embedder):
        """재작성 후 재검색 → reflector 적용 전체 흐름"""
        # 첫 검색은 빈 결과, 재작성 후 결과 있음
        call_count = 0
        idx = MagicMock()
        def smart_query(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"matches": []}
            return {"matches": [
                {"metadata": {"text": "재작성 후 찾은 패턴", "category": "logic", "source": "lib"}, "score": 0.88}
            ]}
        idx.query.side_effect = smart_query

        rag = AgenticRAG(idx, embedder)
        results = rag.search_with_fallback(
            "원본 쿼리",
            rewriter=lambda q: "더 구체적인 쿼리",
            reflector=lambda q, t: True,
            min_results=1,
        )
        assert call_count == 2  # 2회 검색
        assert len(results) == 1
        assert results[0].text == "재작성 후 찾은 패턴"
