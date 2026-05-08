"""
피지수 Cold Tier — ChromaDB 연동
망각된 노트 → ChromaDB 저장 → 벡터 유사도 검색 (데자뷔 소환)
"""

import hashlib
from pathlib import Path
from datetime import datetime
import frontmatter
import chromadb

VAULT_ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = VAULT_ROOT / "archive"
CHROMA_DIR = VAULT_ROOT / ".chromadb"
LOG_FILE = VAULT_ROOT / "wiki" / "log.md"

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_or_create_collection(
    name="physis_cold_memory",
    metadata={"description": "피지수 망각 기억 — Cold Tier"}
)


def _doc_id(path: Path) -> str:
    return hashlib.md5(path.name.encode()).hexdigest()


def ingest(path: Path):
    """망각된 노트를 ChromaDB에 저장"""
    try:
        post = frontmatter.load(str(path))
        text = post.content.strip()
        if not text:
            return
    except Exception:
        return

    doc_id = _doc_id(path)
    meta = {
        "filename": path.name,
        "importance": float(post.metadata.get("importance", 0.5)),
        "outcome_score": float(post.metadata.get("outcome_score", 0.0)),
        "forgotten_at": datetime.now().isoformat(),
    }

    collection.upsert(documents=[text], metadatas=[meta], ids=[doc_id])

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n- [{now}] ❄️ Cold Tier 저장: {path.name}")
    print(f"  [Cold Tier] {path.name} → ChromaDB 저장")


def recall(query: str, n: int = 3) -> list[dict]:
    """데자뷔 소환 — 의미 유사도로 망각 기억 검색"""
    try:
        results = collection.query(query_texts=[query], n_results=min(n, collection.count()))
    except Exception:
        return []

    hits = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        hits.append({"content": doc[:300], "meta": meta})
    return hits


def sync_archive():
    """archive/ 폴더의 파일을 ChromaDB로 일괄 이관"""
    if not ARCHIVE_DIR.exists():
        return
    count = 0
    for path in ARCHIVE_DIR.glob("*.md"):
        ingest(path)
        count += 1
    print(f"[Cold Tier] archive/ → ChromaDB 이관 완료: {count}개")


def stats():
    count = collection.count()
    print(f"[Cold Tier] 저장된 망각 기억: {count}개")
    return count


if __name__ == "__main__":
    sync_archive()
    stats()
    # 테스트 쿼리
    if collection.count() > 0:
        print("\n[데자뷔 테스트] '홍익인간' 검색:")
        hits = recall("홍익인간")
        for h in hits:
            print(f"  - {h['meta']['filename']}: {h['content'][:80]}...")
