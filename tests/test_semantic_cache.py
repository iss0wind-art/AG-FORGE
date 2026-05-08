"""
시맨틱 캐시 테스트 — TDD RED 단계
Redis는 mock 처리. 실제 Redis 없이 실행 가능.
"""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, call
from scripts.semantic_cache import SemanticCache


# ──────────────────────────────────────────
# 픽스처
# ──────────────────────────────────────────

@pytest.fixture
def embedder():
    e = MagicMock()
    e.embed.side_effect = lambda text: [hash(text) % 100 / 100.0] * 768
    return e

@pytest.fixture
def redis_miss(embedder):
    """캐시 미스 상태의 Redis mock."""
    r = MagicMock()
    r.vector_search.return_value = []
    return r

@pytest.fixture
def redis_hit(embedder):
    """캐시 히트 상태의 Redis mock (score=0.98)."""
    r = MagicMock()
    r.vector_search.return_value = [
        {"score": 0.98, "payload": "캐시된 이전 응답입니다."}
    ]
    return r

@pytest.fixture
def redis_low_score():
    """유사도 낮은 Redis mock (score=0.80, 임계값 미달)."""
    r = MagicMock()
    r.vector_search.return_value = [
        {"score": 0.80, "payload": "관련 없는 캐시"}
    ]
    return r


# ──────────────────────────────────────────
# __init__ 테스트
# ──────────────────────────────────────────

class TestSemanticCacheInit:

    def test_stores_threshold(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder, similarity_threshold=0.90)
        assert cache.similarity_threshold == 0.90

    def test_default_threshold_is_095(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder)
        assert cache.similarity_threshold == 0.95


# ──────────────────────────────────────────
# get 테스트
# ──────────────────────────────────────────

class TestGet:

    def test_miss_returns_none(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder)
        assert cache.get("새로운 쿼리") is None

    def test_hit_returns_cached_response(self, redis_hit, embedder):
        cache = SemanticCache(redis_hit, embedder)
        result = cache.get("이전에 물어봤던 질문")
        assert result == "캐시된 이전 응답입니다."

    def test_low_score_returns_none(self, redis_low_score, embedder):
        """유사도가 임계값 미달이면 미스로 처리."""
        cache = SemanticCache(redis_low_score, embedder)
        assert cache.get("다른 질문") is None

    def test_embeds_query_on_get(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder)
        cache.get("테스트 쿼리")
        embedder.embed.assert_called_once_with("테스트 쿼리")

    def test_searches_redis_with_query_vector(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder)
        cache.get("테스트 쿼리")
        redis_miss.vector_search.assert_called_once()


# ──────────────────────────────────────────
# set 테스트
# ──────────────────────────────────────────

class TestSet:

    def test_set_calls_vector_set(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder)
        cache.set("질문", "답변")
        redis_miss.vector_set.assert_called_once()

    def test_set_embeds_query(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder)
        cache.set("질문", "답변")
        embedder.embed.assert_called_once_with("질문")

    def test_set_stores_response_as_payload(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder)
        cache.set("질문", "저장할 응답")
        args = redis_miss.vector_set.call_args
        # payload 인자에 응답이 포함되어야 함
        assert "저장할 응답" in str(args)


# ──────────────────────────────────────────
# get_or_generate 테스트
# ──────────────────────────────────────────

class TestGetOrGenerate:

    def test_miss_calls_generator(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder)
        generator = MagicMock(return_value="새로 생성된 응답")
        response, hit = cache.get_or_generate("새 질문", generator)
        generator.assert_called_once_with("새 질문")
        assert response == "새로 생성된 응답"

    def test_miss_returns_cache_hit_false(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder)
        _, hit = cache.get_or_generate("새 질문", lambda q: "응답")
        assert hit is False

    def test_miss_stores_result_in_cache(self, redis_miss, embedder):
        cache = SemanticCache(redis_miss, embedder)
        cache.get_or_generate("새 질문", lambda q: "새 응답")
        redis_miss.vector_set.assert_called_once()

    def test_hit_skips_generator(self, redis_hit, embedder):
        cache = SemanticCache(redis_hit, embedder)
        generator = MagicMock(return_value="절대 호출되면 안 됨")
        response, hit = cache.get_or_generate("이전 질문", generator)
        generator.assert_not_called()
        assert response == "캐시된 이전 응답입니다."

    def test_hit_returns_cache_hit_true(self, redis_hit, embedder):
        cache = SemanticCache(redis_hit, embedder)
        _, hit = cache.get_or_generate("이전 질문", lambda q: "")
        assert hit is True

    def test_hit_does_not_store_again(self, redis_hit, embedder):
        """캐시 히트 시 Redis에 다시 저장하면 안 된다."""
        cache = SemanticCache(redis_hit, embedder)
        cache.get_or_generate("이전 질문", lambda q: "")
        redis_hit.vector_set.assert_not_called()

    def test_cost_saving_scenario(self, redis_hit, embedder):
        """동일 쿼리 10회 → 9회는 캐시 히트, LLM 1회만 호출."""
        call_count = 0
        def expensive_generator(q):
            nonlocal call_count
            call_count += 1
            return "비싼 LLM 응답"

        # 첫 번째는 miss (저장)
        miss_cache = SemanticCache(MagicMock(
            vector_search=MagicMock(return_value=[]),
            vector_set=MagicMock()
        ), embedder)
        miss_cache.get_or_generate("반복 질문", expensive_generator)

        # 이후는 hit
        for _ in range(9):
            cache = SemanticCache(redis_hit, embedder)
            cache.get_or_generate("반복 질문", expensive_generator)

        assert call_count == 1, f"LLM이 {call_count}회 호출됨 (1회여야 함)"
