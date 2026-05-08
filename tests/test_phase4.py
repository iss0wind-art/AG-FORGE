"""
Phase 4 테스트 — embedding / agentic_rag / auto_archive
모든 외부 API(Pinecone, Google Embedding)는 mock 처리.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, call

from scripts.embedding import chunk_document, embed_and_store, migrate_library
from scripts.agentic_rag import AgenticRAG, RetrievedChunk
from scripts.auto_archive import (
    check_file_size,
    archive_layer,
    run_archive_check,
    ARCHIVE_THRESHOLD_KB,
    BRAIN_ROOT,
)


# ──────────────────────────────────────────
# 공통 픽스처
# ──────────────────────────────────────────

@pytest.fixture
def fake_embedder():
    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 768  # 768-dim 벡터
    return embedder


@pytest.fixture
def fake_index():
    index = MagicMock()
    index.query.return_value = {
        "matches": [
            {"metadata": {"text": "Ruby 최적화 패턴", "category": "logic", "source": "logic_rb"}, "score": 0.92},
            {"metadata": {"text": "Rails 캐싱 전략", "category": "logic", "source": "logic_rb"}, "score": 0.85},
            {"metadata": {"text": "DB 인덱스 설계", "category": "logic", "source": "logic_rb"}, "score": 0.78},
        ]
    }
    return index


# ──────────────────────────────────────────
# chunk_document 테스트
# ──────────────────────────────────────────

class TestChunkDocument:

    def test_short_text_returns_single_chunk(self):
        text = "짧은 텍스트"
        chunks = chunk_document(text, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_is_split(self):
        text = "A" * 1200
        chunks = chunk_document(text, chunk_size=500, overlap=50)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        text = "A" * 600
        chunks = chunk_document(text, chunk_size=500, overlap=100)
        # 두 번째 청크는 첫 번째 청크의 끝 100자를 포함해야 한다
        assert chunks[1][:100] == chunks[0][-100:]

    def test_no_chunk_exceeds_chunk_size(self):
        text = "B" * 2000
        chunks = chunk_document(text, chunk_size=500, overlap=50)
        assert all(len(c) <= 500 for c in chunks)

    def test_empty_text_returns_empty_list(self):
        assert chunk_document("") == []

    def test_custom_chunk_size(self):
        text = "C" * 300
        chunks = chunk_document(text, chunk_size=100, overlap=10)
        assert len(chunks) >= 3


# ──────────────────────────────────────────
# embed_and_store 테스트
# ──────────────────────────────────────────

class TestEmbedAndStore:

    def test_returns_chunk_count(self, fake_index, fake_embedder):
        text = "테스트 문서 내용 " * 50  # 충분히 긴 텍스트
        count = embed_and_store("doc-001", text, "logic", fake_index, fake_embedder)
        assert count > 0

    def test_calls_embedder_per_chunk(self, fake_index, fake_embedder):
        text = "X" * 1200  # chunk_size=500이면 3청크
        embed_and_store("doc-002", text, "logic", fake_index, fake_embedder)
        assert fake_embedder.embed.call_count >= 1

    def test_upserts_to_index(self, fake_index, fake_embedder):
        embed_and_store("doc-003", "테스트", "emotion", fake_index, fake_embedder)
        assert fake_index.upsert.called

    def test_metadata_contains_category(self, fake_index, fake_embedder):
        embed_and_store("doc-004", "내용", "decisions", fake_index, fake_embedder)
        upsert_call = fake_index.upsert.call_args
        vectors = upsert_call[1]["vectors"] if upsert_call[1] else upsert_call[0][0]
        assert vectors[0]["metadata"]["category"] == "decisions"

    def test_metadata_contains_source(self, fake_index, fake_embedder):
        embed_and_store("my-doc-id", "내용", "logic", fake_index, fake_embedder)
        upsert_call = fake_index.upsert.call_args
        vectors = upsert_call[1]["vectors"] if upsert_call[1] else upsert_call[0][0]
        assert vectors[0]["metadata"]["source"] == "my-doc-id"


# ──────────────────────────────────────────
# migrate_library 테스트
# ──────────────────────────────────────────

class TestMigrateLibrary:

    def test_migrates_existing_file(self, tmp_path, fake_index, fake_embedder):
        lib_file = tmp_path / "library-logic.md"
        lib_file.write_text("# 라이브러리\n\n과거 패턴 내용입니다.", encoding="utf-8")

        count = migrate_library(lib_file, "logic", fake_index, fake_embedder)
        assert count >= 1

    def test_raises_on_missing_file(self, fake_index, fake_embedder):
        with pytest.raises(FileNotFoundError):
            migrate_library(Path("nonexistent.md"), "logic", fake_index, fake_embedder)


# ──────────────────────────────────────────
# AgenticRAG 테스트
# ──────────────────────────────────────────

class TestAgenticRAG:

    def test_init_stores_threshold(self, fake_index, fake_embedder):
        rag = AgenticRAG(fake_index, fake_embedder, similarity_threshold=0.80)
        assert rag.similarity_threshold == 0.80

    def test_search_returns_chunks(self, fake_index, fake_embedder):
        rag = AgenticRAG(fake_index, fake_embedder)
        results = rag.search("Ruby 최적화", top_k=3)
        assert len(results) == 3
        assert all(isinstance(r, RetrievedChunk) for r in results)

    def test_search_filters_by_threshold(self, fake_index, fake_embedder):
        """유사도가 threshold 미만인 결과는 제외된다."""
        fake_index.query.return_value = {
            "matches": [
                {"metadata": {"text": "관련 내용", "category": "logic", "source": "test"}, "score": 0.90},
                {"metadata": {"text": "무관한 내용", "category": "logic", "source": "test"}, "score": 0.50},
            ]
        }
        rag = AgenticRAG(fake_index, fake_embedder, similarity_threshold=0.75)
        results = rag.search("쿼리", top_k=2)
        assert len(results) == 1
        assert results[0].score == 0.90

    def test_search_embeds_query(self, fake_index, fake_embedder):
        rag = AgenticRAG(fake_index, fake_embedder)
        rag.search("최적화 패턴 찾아줘")
        fake_embedder.embed.assert_called_once_with("최적화 패턴 찾아줘")

    def test_build_context_joins_chunks(self, fake_index, fake_embedder):
        rag = AgenticRAG(fake_index, fake_embedder)
        context = rag.build_context("Ruby 패턴")
        assert "Ruby 최적화 패턴" in context
        assert "Rails 캐싱 전략" in context

    def test_build_context_returns_string(self, fake_index, fake_embedder):
        rag = AgenticRAG(fake_index, fake_embedder)
        result = rag.build_context("쿼리")
        assert isinstance(result, str)

    def test_empty_results_returns_empty_context(self, fake_index, fake_embedder):
        fake_index.query.return_value = {"matches": []}
        rag = AgenticRAG(fake_index, fake_embedder)
        assert rag.build_context("쿼리") == ""


# ──────────────────────────────────────────
# auto_archive 테스트
# ──────────────────────────────────────────

class TestCheckFileSize:

    def test_small_file_returns_false(self, tmp_path):
        f = tmp_path / "small.md"
        f.write_bytes(b"x" * 1024)  # 1KB
        assert check_file_size(f, threshold_kb=40) is False

    def test_large_file_returns_true(self, tmp_path):
        f = tmp_path / "large.md"
        f.write_bytes(b"x" * 41 * 1024)  # 41KB
        assert check_file_size(f, threshold_kb=40) is True

    def test_exactly_at_threshold_returns_false(self, tmp_path):
        f = tmp_path / "exact.md"
        f.write_bytes(b"x" * 40 * 1024)  # 정확히 40KB
        assert check_file_size(f, threshold_kb=40) is False


class TestArchiveLayer:

    def test_skips_small_file(self, tmp_path, fake_index, fake_embedder):
        f = tmp_path / "logic_rb.md"
        f.write_bytes(b"x" * 1024)  # 1KB
        result = archive_layer(f, "logic", fake_index, fake_embedder)
        assert result is False
        fake_index.upsert.assert_not_called()

    def test_archives_large_file(self, tmp_path, fake_index, fake_embedder):
        f = tmp_path / "logic_rb.md"
        f.write_bytes(b"content " * 6000)  # ~41KB
        result = archive_layer(f, "logic", fake_index, fake_embedder)
        assert result is True
        assert fake_index.upsert.called

    def test_resets_file_after_archive(self, tmp_path, fake_index, fake_embedder):
        f = tmp_path / "logic_rb.md"
        f.write_bytes(b"X" * 41 * 1024)
        archive_layer(f, "logic", fake_index, fake_embedder)
        content = f.read_text(encoding="utf-8")
        # 초기화 후 파일이 40KB보다 훨씬 작아야 한다
        assert len(content) < 1024

    def test_reset_file_contains_archive_notice(self, tmp_path, fake_index, fake_embedder):
        f = tmp_path / "logic_rb.md"
        f.write_bytes(b"X" * 41 * 1024)
        archive_layer(f, "logic", fake_index, fake_embedder)
        content = f.read_text(encoding="utf-8")
        assert "아카이브" in content or "archive" in content.lower()


class TestRunArchiveCheck:

    def test_returns_list_of_archived_files(self, tmp_path, fake_index, fake_embedder, monkeypatch):
        monkeypatch.setattr("scripts.auto_archive.BRAIN_ROOT", tmp_path)

        # logic_rb.md만 초과
        logic = tmp_path / "logic_rb.md"
        logic.write_bytes(b"X" * 41 * 1024)

        emotion = tmp_path / "emotion_ui.md"
        emotion.write_bytes(b"x" * 1024)

        judgment = tmp_path / "judgment.md"
        judgment.write_bytes(b"x" * 1024)

        archived = run_archive_check(fake_index, fake_embedder)
        assert "logic_rb.md" in archived
        assert "emotion_ui.md" not in archived

    def test_empty_when_no_files_exceed(self, tmp_path, fake_index, fake_embedder, monkeypatch):
        monkeypatch.setattr("scripts.auto_archive.BRAIN_ROOT", tmp_path)

        for name in ["logic_rb.md", "emotion_ui.md", "judgment.md"]:
            (tmp_path / name).write_bytes(b"x" * 1024)

        assert run_archive_check(fake_index, fake_embedder) == []
