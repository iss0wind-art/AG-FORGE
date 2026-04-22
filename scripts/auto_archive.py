"""
자동 아카이브 — auto_archive.py
레이어 파일이 40KB를 초과하면 Vector DB로 이관하고 원본을 초기화한다.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from scripts.embedding import VectorIndex, EmbeddingClient, embed_and_store

ARCHIVE_THRESHOLD_KB = 40
BRAIN_ROOT = Path(__file__).parent.parent

LAYER_TO_CATEGORY: dict[str, str] = {
    "logic_rb.md":   "logic",
    "emotion_ui.md": "emotion",
    "judgment.md":   "decisions",
}


def check_file_size(filepath: Path, threshold_kb: int = ARCHIVE_THRESHOLD_KB) -> bool:
    """파일 크기가 임계값을 초과하면 True를 반환한다."""
    return filepath.stat().st_size / 1024 > threshold_kb


def archive_layer(
    source_file: Path,
    category: str,
    index: VectorIndex,
    embedder: EmbeddingClient,
) -> bool:
    """파일 내용을 Vector DB로 이관하고 원본을 초기화한다. 아카이브 실행 여부를 반환한다."""
    if not check_file_size(source_file):
        return False

    content = source_file.read_text(encoding="utf-8")
    doc_id = f"{source_file.stem}-archived-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    embed_and_store(doc_id, content, category, index, embedder)

    reset_text = (
        f"# {source_file.stem} — 아카이브됨\n\n"
        f"이전 내용이 Vector DB로 이관되었습니다. ({doc_id})\n"
        f"아카이브 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"최근 작업은 이 아래에만 기록됩니다.\n"
    )
    source_file.write_text(reset_text, encoding="utf-8")
    return True


def run_archive_check(
    index: VectorIndex,
    embedder: EmbeddingClient,
) -> list[str]:
    """모든 레이어 파일을 검사하여 초과 파일을 아카이브한다. 아카이브된 파일명 목록을 반환한다."""
    archived = []
    for filename, category in LAYER_TO_CATEGORY.items():
        filepath = BRAIN_ROOT / filename
        if filepath.exists() and archive_layer(filepath, category, index, embedder):
            archived.append(filename)
    return archived
