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


class GoogleEmbeddingClient:
    """Google GenAI(v1) text-embedding-004 클라이언트."""

    def __init__(self, api_key: str) -> None:
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-embedding-001"

    def embed(self, text: str) -> list[float]:
        try:
            result = self.client.models.embed_content(
                model=self.model,
                contents=text,
                config=dict(task_type="RETRIEVAL_DOCUMENT")
            )
            return result.embeddings[0].values
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                # Gemini 쿼터 초과 → TF-IDF 폴백
                return SimpleTFIDFEmbedder().embed(text)
            raise


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

    text = None
    for enc in ["utf-8", "cp949", "latin-1"]:
        try:
            text = filepath.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
            
    if text is None:
        text = filepath.read_text(encoding="utf-8", errors="replace")

    doc_id = f"{filepath.stem}-{datetime.now().strftime('%Y%m%d')}"
    return embed_and_store(doc_id, text, category, index, embedder)


class ChromaVectorIndex:
    """ChromaDB 영구 로컬 VectorIndex 구현체."""

    def __init__(
        self,
        persist_path: str = "d:/Git/AG-Forge/library/vector_db",
        collection_name: str = "physis_brain",
        expected_dim: int | None = None,
    ) -> None:
        import chromadb
        self._client = chromadb.PersistentClient(path=persist_path)
        self._col = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        # 임베더 차원이 기존 컬렉션과 다르면 컬렉션을 재생성한다.
        if expected_dim is not None and self._col.count() > 0:
            try:
                existing = self._col.get(limit=1, include=["embeddings"])
                embs = existing.get("embeddings")
                if embs is not None and len(embs) > 0:
                    stored_dim = len(embs[0])
                    if stored_dim != expected_dim:
                        import sys as _sys
                        print(
                            f"[ChromaVectorIndex] 차원 불일치 감지 "
                            f"(저장:{stored_dim} vs 신규:{expected_dim}). "
                            f"컬렉션 재생성.",
                            file=_sys.stderr,
                        )
                        self._client.delete_collection(collection_name)
                        self._col = self._client.get_or_create_collection(
                            name=collection_name,
                            metadata={"hnsw:space": "cosine"},
                        )
            except Exception:
                pass  # 확인 실패 시 그대로 진행

    def upsert(self, vectors: list[dict]) -> None:
        """벡터 목록을 ChromaDB에 저장한다. 기존 id면 업데이트, 없으면 추가한다."""
        if not vectors:
            return
        ids = [v["id"] for v in vectors]
        embeddings = [v["values"] for v in vectors]
        metadatas = [v.get("metadata", {}) for v in vectors]
        existing = self._col.get(ids=ids, include=[])
        existing_ids = set(existing["ids"])
        new_ids, new_embs, new_metas = [], [], []
        upd_ids, upd_embs, upd_metas = [], [], []
        for vid, emb, meta in zip(ids, embeddings, metadatas):
            if vid in existing_ids:
                upd_ids.append(vid)
                upd_embs.append(emb)
                upd_metas.append(meta)
            else:
                new_ids.append(vid)
                new_embs.append(emb)
                new_metas.append(meta)
        if new_ids:
            self._col.add(ids=new_ids, embeddings=new_embs, metadatas=new_metas)
        if upd_ids:
            self._col.update(ids=upd_ids, embeddings=upd_embs, metadatas=upd_metas)

    def query(
        self,
        vector: list[float],
        top_k: int = 5,
        include_metadata: bool = True,
    ) -> dict:
        """벡터와 가장 유사한 항목을 조회한다. 기존 코드와 호환되는 형식으로 반환한다."""
        include_fields = ["distances"]
        if include_metadata:
            include_fields.append("metadatas")
        results = self._col.query(
            query_embeddings=[vector],
            n_results=min(top_k, self._col.count()) or 1,
            include=include_fields,
        )
        matches = []
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0] if include_metadata else [{}] * len(ids)
        for vid, dist, meta in zip(ids, distances, metadatas):
            matches.append({
                "id": vid,
                "score": 1.0 - dist,
                "metadata": meta or {},
            })
        return {"matches": matches}

    def count(self) -> int:
        """저장된 벡터 수를 반환한다."""
        return self._col.count()


class SimpleTFIDFEmbedder:
    """GEMINI_API_KEY 없을 때 사용하는 sklearn-free TF-IDF 폴백 임베더."""

    DIM = 768

    def embed(self, text: str) -> list[float]:
        """텍스트를 768차원 L2 정규화된 벡터로 변환한다."""
        import re
        import math
        tokens = re.findall(r"[^\s\W]+", text.lower())
        vec = [0.0] * self.DIM
        for token in tokens:
            idx = hash(token) % self.DIM
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]
        return vec


def build_default_embedder() -> EmbeddingClient:
    """환경에 따라 Google 또는 TF-IDF 임베더를 자동 선택한다.
    Gemini 쿼터 초과 시 TF-IDF로 고정 (차원 불일치 방지).
    """
    import os
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        try:
            client = GoogleEmbeddingClient(api_key=key)
            # 쿼터 사전 확인 — 실패 시 TF-IDF 사용
            client.embed("probe")
            return client
        except Exception:
            pass
    return SimpleTFIDFEmbedder()
