"""
시맨틱 캐싱 레이어 — semantic_cache.py
동일·유사 쿼리는 LLM 호출 없이 Redis에서 즉시 반환한다. (0원)
임계값: similarity >= 0.95
"""
from __future__ import annotations
import hashlib
from typing import Callable, Protocol


class RedisVectorClient(Protocol):
    """Redis Stack Vector Search 추상 인터페이스."""
    def vector_set(self, key: str, vector: list[float], payload: str) -> None: ...
    def vector_search(self, vector: list[float], top_k: int) -> list[dict]: ...


class SemanticCache:
    def __init__(
        self,
        redis_client: RedisVectorClient,
        embedder,
        similarity_threshold: float = 0.95,
    ) -> None:
        self._redis = redis_client
        self._embedder = embedder
        self.similarity_threshold = similarity_threshold

    def get(self, query: str) -> str | None:
        """캐시 히트 시 응답 반환, 미스 시 None."""
        vector = self._embedder.embed(query)
        results = self._redis.vector_search(vector=vector, top_k=1)
        if results and results[0]["score"] >= self.similarity_threshold:
            return results[0]["payload"]
        return None

    def set(self, query: str, response: str) -> None:
        """쿼리-응답 쌍을 Redis Vector DB에 저장한다."""
        vector = self._embedder.embed(query)
        key = f"cache:{hashlib.md5(query.encode()).hexdigest()}"
        self._redis.vector_set(key=key, vector=vector, payload=response)

    def get_or_generate(
        self,
        query: str,
        generator: Callable[[str], str],
    ) -> tuple[str, bool]:
        """
        캐시 히트: (캐시된 응답, True) 반환.
        캐시 미스: generator 호출 후 저장 → (새 응답, False) 반환.
        """
        cached = self.get(query)
        if cached is not None:
            return cached, True

        response = generator(query)
        self.set(query, response)
        return response, False
