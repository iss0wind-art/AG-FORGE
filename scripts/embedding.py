"""
해마 임베딩 파이프라인 — embedding.py
문서를 청크로 분할하고 Google text-embedding-004로 벡터화하여 Pinecone에 저장한다.
"""
from __future__ import annotations
from pathlib import Path
from typing import Protocol
from datetime import datetime


class VectorIndex(Protocol):
    """Pinecone Index와 호환되는 추상 인터페이스."""
    def upsert(self, vectors: list[dict]) -> None: ...
    def query(self, vector: list[float], top_k: int, include_metadata: bool) -> dict: ...


class EmbeddingClient(Protocol):
    """Google / OpenAI 임베딩 클라이언트 추상 인터페이스."""
    def embed(self, text: str) -> list[float]: ...


def chunk_document(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """텍스트를 겹침 있는 청크로 분할한다."""
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap

    return chunks


def embed_and_store(
    doc_id: str,
    text: str,
    category: str,
    index: VectorIndex,
    embedder: EmbeddingClient,
) -> int:
    """텍스트를 청킹 → 임베딩 → Pinecone 저장. 저장된 청크 수를 반환한다."""
    chunks = chunk_document(text)
    if not chunks:
        return 0

    vectors = []
    for i, chunk in enumerate(chunks):
        embedding = embedder.embed(chunk)
        vectors.append({
            "id": f"{doc_id}_{i}",
            "values": embedding,
            "metadata": {
                "source": doc_id,
                "category": category,
                "chunk_index": i,
                "text": chunk[:200],
            },
        })

    index.upsert(vectors=vectors)
    return len(vectors)


def migrate_library(
    filepath: Path,
    category: str,
    index: VectorIndex,
    embedder: EmbeddingClient,
) -> int:
    """library-*.md 파일을 읽어 Vector DB로 마이그레이션한다. 저장된 청크 수를 반환한다."""
    if not filepath.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")

    text = filepath.read_text(encoding="utf-8")
    doc_id = f"{filepath.stem}-{datetime.now().strftime('%Y%m%d')}"
    return embed_and_store(doc_id, text, category, index, embedder)
