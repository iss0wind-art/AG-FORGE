"""
해마 Agentic RAG — agentic_rag.py
시맨틱 서치로 관련 기억만 추출하여 brain_loader에 주입한다.

강화:
  - 결과 부족 시 쿼리 자동 재작성 (rewrite_query)
  - 검색 결과 신뢰도 자기 검증 (self_reflect)

Phase 3 HyperRAG:
  - 3단계 검색 파이프라인 (직접 → 그래프 횡단 → CMA 필터)
  - Token Budget + Stop Condition (환경변수 제어)
  - SACHOCHEONG 분관 인터페이스 (읽기 전용)
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
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


# ── SACHOCHEONG 분관 인터페이스 ──────────────────────────────────────────────────

SACHOCHEONG_PATH = Path("D:/Git/DREAM_FAC/SACHOCHEONG")


def load_sachocheong_context() -> str:
    """분관 SACHOCHEONG에 새 기록이 있으면 최우선 컨텍스트로 반환. 읽기 전용."""
    log_dir = SACHOCHEONG_PATH / "log"
    if not log_dir.exists():
        return ""
    files = sorted(
        log_dir.glob("*.md"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return ""
    return files[0].read_text(encoding="utf-8", errors="replace")[:500]


# ── HyperRAG ─────────────────────────────────────────────────────────────────

MAX_TOKENS_DEFAULT = 2000
STOP_SCORE_DEFAULT = 0.95


class HyperRAG:
    """
    Phase 3 HyperRAG — 3단계 검색 파이프라인.

    1차: 직접 검색 (top_k=3)
    2차: 카테고리 기반 그래프 횡단 (최대 2홉, 홉당 top_k=2)
    3차: CMA 필터 (BLOCK 위반 청크 제거)

    Token Budget: HYPER_RAG_MAX_TOKENS (기본 2000)
    Stop Condition: HYPER_RAG_STOP_SCORE (기본 0.95) — 충분히 좋은 결과 즉시 종료
    """

    def __init__(
        self,
        index: VectorIndex,
        embedder: EmbeddingClient,
        similarity_threshold: float = 0.75,
    ) -> None:
        self.index = index
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.max_tokens = int(
            os.environ.get("HYPER_RAG_MAX_TOKENS", str(MAX_TOKENS_DEFAULT))
        )
        self.stop_score = float(
            os.environ.get("HYPER_RAG_STOP_SCORE", str(STOP_SCORE_DEFAULT))
        )

    # ── 내부 검색 헬퍼 ──────────────────────────────────────────────────────────

    def _raw_search(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """threshold 필터 없이 Vector DB를 조회한다 (내부용)."""
        query_vector = self.embedder.embed(query)
        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
        )
        return [
            RetrievedChunk(
                text=match["metadata"].get("text", ""),
                score=match["score"],
                category=match["metadata"].get("category", ""),
                source=match["metadata"].get("source", ""),
            )
            for match in results.get("matches", [])
            if match["score"] >= self.similarity_threshold
        ]

    # ── 1단계: 직접 검색 ─────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """쿼리와 유사한 청크를 Vector DB에서 검색한다."""
        return self._raw_search(query, top_k=top_k)

    # ── 2단계: 그래프 횡단 ───────────────────────────────────────────────────────

    def traverse_graph(
        self,
        chunks: list[RetrievedChunk],
        max_hops: int = 2,
    ) -> list[RetrievedChunk]:
        """
        chunk의 category를 기반으로 같은 카테고리의 다른 청크를 검색한다.
        ChromaDB where 필터 사용: {"category": chunk.category}
        최대 max_hops홉, 홉당 top_k=2로 제한.
        Token Budget 초과 시 중단.
        """
        lateral: list[RetrievedChunk] = []
        seen_sources: set[str] = {c.source for c in chunks}
        accumulated_tokens = sum(len(c.text.split()) for c in chunks)

        frontier = list(chunks)
        for _hop in range(max_hops):
            if not frontier:
                break
            next_frontier: list[RetrievedChunk] = []
            for chunk in frontier:
                if not chunk.category:
                    continue
                if accumulated_tokens >= self.max_tokens:
                    break
                # ChromaDB where 필터로 같은 카테고리 조회
                query_vector = self.embedder.embed(chunk.text)
                try:
                    results = self.index.query(
                        vector=query_vector,
                        top_k=2,
                        include_metadata=True,
                    )
                except Exception:
                    continue
                for match in results.get("matches", []):
                    meta = match.get("metadata", {})
                    if meta.get("category", "") != chunk.category:
                        continue
                    source = meta.get("source", "")
                    if source in seen_sources:
                        continue
                    score = match["score"]
                    if score < self.similarity_threshold:
                        continue
                    new_chunk = RetrievedChunk(
                        text=meta.get("text", ""),
                        score=score,
                        category=meta.get("category", ""),
                        source=source,
                    )
                    lateral.append(new_chunk)
                    next_frontier.append(new_chunk)
                    seen_sources.add(source)
                    accumulated_tokens += len(new_chunk.text.split())
                    if accumulated_tokens >= self.max_tokens:
                        break
            frontier = next_frontier

        return lateral

    # ── 3단계: CMA 필터 ──────────────────────────────────────────────────────────

    def cma_filter(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """BLOCK 위반 청크만 제거한다. WARN은 통과."""
        try:
            from scripts.cma_gate import layer0_check, ViolationLevel
        except ImportError:
            return chunks

        filtered: list[RetrievedChunk] = []
        for chunk in chunks:
            result = layer0_check("", chunk.text)
            if result is not None and result.level == ViolationLevel.BLOCK:
                continue
            filtered.append(chunk)
        return filtered

    # ── 통합 파이프라인 ──────────────────────────────────────────────────────────

    def search_pipeline(self, query: str) -> list[RetrievedChunk]:
        """
        3단계 검색 파이프라인 실행.

        1차 직접 검색 → Stop Condition 확인 → 2차 그래프 횡단 → 3차 CMA 필터
        """
        # 1차: 직접 검색
        direct_chunks = self.search(query, top_k=3)

        # Stop Condition: 최상위 결과가 충분히 좋으면 즉시 반환
        if direct_chunks and direct_chunks[0].score >= self.stop_score:
            return self.cma_filter(direct_chunks)

        # 2차: 카테고리 기반 그래프 횡단 (최대 2홉)
        lateral_chunks = self.traverse_graph(direct_chunks, max_hops=2)

        # 3차: CMA 필터 통과한 것만
        combined = direct_chunks + lateral_chunks
        return self.cma_filter(combined)

    # ── 컨텍스트 빌더 ────────────────────────────────────────────────────────────

    def build_context(self, query: str) -> str:
        """SACHOCHEONG 우선 컨텍스트 + 검색 파이프라인 결과를 조합한다."""
        sachocheong = load_sachocheong_context()
        chunks = self.search_pipeline(query)
        parts: list[str] = []
        if sachocheong:
            parts.append(f"[사초청 우선 컨텍스트]\n{sachocheong}")
        parts.extend(chunk.text for chunk in chunks)
        return "\n---\n".join(parts)
