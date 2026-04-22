"""
해마 Agentic RAG — agentic_rag.py
시맨틱 서치로 관련 기억만 추출하여 brain_loader에 주입한다.

강화:
  - 결과 부족 시 쿼리 자동 재작성 (rewrite_query)
  - 검색 결과 신뢰도 자기 검증 (self_reflect)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from scripts.embedding import VectorIndex, EmbeddingClient


@dataclass
class RetrievedChunk:
    text: str
    score: float
    category: str
    source: str


class AgenticRAG:
    def __init__(
        self,
        index: VectorIndex,
        embedder: EmbeddingClient,
        similarity_threshold: float = 0.75,
    ) -> None:
        self.index = index
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold

    def search(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """쿼리와 유사한 청크를 Vector DB에서 검색한다. threshold 미만은 제외."""
        query_vector = self.embedder.embed(query)
        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
        )
        return [
            RetrievedChunk(
                text=match["metadata"]["text"],
                score=match["score"],
                category=match["metadata"].get("category", ""),
                source=match["metadata"].get("source", ""),
            )
            for match in results.get("matches", [])
            if match["score"] >= self.similarity_threshold
        ]

    def build_context(self, query: str, top_k: int = 3) -> str:
        """검색 결과를 LLM 컨텍스트 문자열로 조합한다."""
        chunks = self.search(query, top_k=top_k)
        if not chunks:
            return ""
        return "\n---\n".join(chunk.text for chunk in chunks)

    def rewrite_query(self, original_query: str, rewriter: Callable[[str], str]) -> str:
        """검색 결과가 부족할 때 쿼리를 재작성한다."""
        return rewriter(original_query)

    def self_reflect(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        reflector: Callable[[str, str], bool],
    ) -> list[RetrievedChunk]:
        """검색된 청크가 쿼리와 실제로 관련 있는지 LLM으로 검증한다."""
        return [c for c in chunks if reflector(query, c.text)]

    def search_with_fallback(
        self,
        query: str,
        top_k: int = 3,
        rewriter: Callable[[str], str] | None = None,
        reflector: Callable[[str, str], bool] | None = None,
        min_results: int = 1,
    ) -> list[RetrievedChunk]:
        """
        강화된 검색:
        1. 기본 검색
        2. 결과 < min_results이고 rewriter 있으면 쿼리 재작성 후 재검색
        3. reflector 있으면 결과 자기 검증 후 통과한 것만 반환
        """
        results = self.search(query, top_k=top_k)

        if len(results) < min_results and rewriter is not None:
            rewritten = self.rewrite_query(query, rewriter)
            results = self.search(rewritten, top_k=top_k)

        if reflector is not None:
            results = self.self_reflect(query, results, reflector)

        return results
