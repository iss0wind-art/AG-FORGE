"""
해마 벡터 DB 초기화 및 관리 — setup_vector_db.py
ChromaDB를 사용하여 로컬 장기기억 저장소를 구축한다.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import chromadb
from chromadb.config import Settings

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "library" / "vector_db"

class ChromaDBIndex:
    """ChromaDB를 이용한 VectorIndex 구현."""

    def __init__(self, collection_name: str = "physis_memory") -> None:
        # DB 경로 보장
        DB_PATH.parent.mkdir(exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(DB_PATH),
            settings=Settings(allow_reset=True)
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def upsert(self, vectors: list[dict]) -> None:
        """
        vectors: list[dict] where each dict has:
            'id': str,
            'values': list[float],
            'metadata': dict
        """
        ids = [v["id"] for v in vectors]
        embeddings = [v["values"] for v in vectors]
        metadatas = [v["metadata"] for v in vectors]

        # ChromaDB는 'documents' 필드도 가질 수 있으나, 여기서는 metadata 내부의 'text'를 사용
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def query(self, vector: list[float], top_k: int, include_metadata: bool) -> dict:
        """
        vector: list[float]
        Returns: dict formatted similarly to Pinecone response for compatibility
        """
        results = self.collection.query(
            query_embeddings=[vector],
            n_results=top_k,
            include=["metadatas", "distances"]
        )

        matches = []
        # results['ids'], results['distances'], results['metadatas']는 리스트의 리스트임 [[...]]
        for i in range(len(results["ids"][0])):
            matches.append({
                "id": results["ids"][0][i],
                "score": 1.0 - results["distances"][0][i], # cosine distance -> similarity
                "metadata": results["metadatas"][0][i]
            })

        return {"matches": matches}

def get_vector_db() -> ChromaDBIndex:
    """기본 Physis 메모리 컬렉션을 반환한다."""
    return ChromaDBIndex()

if __name__ == "__main__":
    print(f"--- Physis 해마(ChromaDB) 초기화 ---")
    idx = get_vector_db()
    print(f"✅ 벡터 저장소 경로: {DB_PATH}")
    print(f"✅ 컬렉션 준비됨: {idx.collection.name}")
