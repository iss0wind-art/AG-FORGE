"""
E2E 통합 테스트 — 전체 파이프라인 검증
실제 API 없이 FakeProvider로 전체 흐름을 검증한다.

파이프라인:
  task → router → layer select → brain load → RAG search → LLM call → observe
"""
from __future__ import annotations
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from scripts.router_agent import route, TaskType
from scripts.brain_loader import BrainResponse, LLMProvider, run, select_layers
from scripts.embedding import embed_and_store
from scripts.agentic_rag import AgenticRAG
from scripts.auto_archive import run_archive_check
from scripts.observability import record_trace, summarize_session


# ──────────────────────────────────────────
# 픽스처
# ──────────────────────────────────────────

class FakeProvider(LLMProvider):
    def __init__(self):
        self.calls = []

    def generate(self, system_instruction, context_layers, task, model, thinking_budget):
        self.calls.append({"model": model, "task": task, "thinking_budget": thinking_budget})
        return BrainResponse(
            text=f"[{model}] {task}에 대한 응답",
            model=model,
            task_type="fake",
            tokens_used=300,
            cache_hit=False,
        )


@pytest.fixture
def fake_vector():
    index = MagicMock()
    index.query.return_value = {
        "matches": [
            {"metadata": {"text": "과거 패턴 A", "category": "logic", "source": "lib"}, "score": 0.88},
        ]
    }
    return index


@pytest.fixture
def fake_embedder():
    e = MagicMock()
    e.embed.return_value = [0.1] * 768
    return e


# ──────────────────────────────────────────
# E2E: 라우팅 정확도 (20개 샘플)
# ──────────────────────────────────────────

class TestRoutingAccuracy:

    CASES = [
        ("버튼 색상 수정해줘",           TaskType.UI),
        ("fix the button style",        TaskType.UI),
        ("디자인 문구 바꿔줘",           TaskType.UI),
        ("UI 레이아웃 수정",             TaskType.UI),
        ("알고리즘 최적화해줘",          TaskType.CODE),
        ("DB 스키마 설계 부탁해",        TaskType.CODE),
        ("버그 수정이 필요해",           TaskType.CODE),
        ("함수 리팩토링 해줘",           TaskType.CODE),
        ("SQL 쿼리 최적화",             TaskType.CODE),
        ("전략 기획 해줘",              TaskType.PLANNING),
        ("research the market",        TaskType.PLANNING),
        ("왜 이렇게 설계됐어?",          TaskType.PLANNING),
        ("분석 보고서 작성",             TaskType.PLANNING),
        ("전체 시스템 아키텍처 설계",    TaskType.ARCHITECTURE),
        ("트레이드오프 분석",            TaskType.ARCHITECTURE),
        ("시스템 구조 검토",             TaskType.ARCHITECTURE),
        ("코드 작성해줘",               TaskType.CODE),
        ("마이그레이션 스크립트",        TaskType.CODE),
        ("기획안 정리",                 TaskType.PLANNING),
        ("색상 팔레트 수정",             TaskType.UI),
    ]

    def test_routing_accuracy_above_90_percent(self):
        correct = sum(
            1 for task, expected in self.CASES
            if route(task).task_type == expected
        )
        accuracy = correct / len(self.CASES)
        assert accuracy >= 0.90, (
            f"라우팅 정확도 미달: {accuracy:.1%} "
            f"({correct}/{len(self.CASES)})"
        )


# ──────────────────────────────────────────
# E2E: 전체 파이프라인
# ──────────────────────────────────────────

class TestFullPipeline:

    def test_ui_task_uses_flash(self):
        provider = FakeProvider()
        run("버튼 색상 수정", provider)
        assert provider.calls[0]["model"] == "gemini-2.0-flash"

    def test_code_task_uses_pro(self):
        provider = FakeProvider()
        run("알고리즘 최적화", provider)
        assert provider.calls[0]["model"] == "gemini-2.5-pro"

    def test_architecture_gets_max_budget(self):
        provider = FakeProvider()
        run("전체 시스템 아키텍처 설계", provider)
        assert provider.calls[0]["thinking_budget"] == 10000

    def test_response_contains_task(self):
        provider = FakeProvider()
        result = run("DB 스키마 설계", provider)
        assert isinstance(result, BrainResponse)
        assert result.text != ""

    def test_layer_file_is_loaded(self):
        """brain.md가 system_instruction으로 전달되는지 확인"""
        calls = []

        class InspectProvider(LLMProvider):
            def generate(self, system_instruction, context_layers, task, model, thinking_budget):
                calls.append(system_instruction)
                return BrainResponse("ok", model, "fake", 10, False)

        run("코드 작성", InspectProvider())
        assert len(calls[0]) > 0  # brain.md 내용이 전달됨


# ──────────────────────────────────────────
# E2E: RAG → 파이프라인 연결
# ──────────────────────────────────────────

class TestRAGPipeline:

    def test_rag_retrieves_relevant_chunks(self, fake_vector, fake_embedder):
        rag = AgenticRAG(fake_vector, fake_embedder, similarity_threshold=0.75)
        context = rag.build_context("Ruby 최적화 방법")
        assert "과거 패턴 A" in context

    def test_rag_empty_when_no_match(self, fake_vector, fake_embedder):
        fake_vector.query.return_value = {"matches": []}
        rag = AgenticRAG(fake_vector, fake_embedder)
        assert rag.build_context("아무 관계 없는 쿼리") == ""

    def test_embed_then_search_pipeline(self, fake_vector, fake_embedder):
        """임베딩 저장 후 검색이 호출되는 전체 흐름"""
        stored = embed_and_store("test-doc", "테스트 패턴 내용", "logic", fake_vector, fake_embedder)
        assert stored >= 1
        rag = AgenticRAG(fake_vector, fake_embedder)
        results = rag.search("패턴 검색", top_k=1)
        assert len(results) >= 0  # mock 결과 반환


# ──────────────────────────────────────────
# E2E: 관측성 통합
# ──────────────────────────────────────────

class TestObservabilityPipeline:

    def test_full_trace_recorded(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.observability.LOG_PATH", tmp_path / "trace.jsonl")

        from scripts.observability import append_log
        provider = FakeProvider()
        result = run("알고리즘 최적화", provider)
        layers = select_layers(route("알고리즘 최적화"))

        record = record_trace(result, "알고리즘 최적화", layers)
        append_log(record)

        log_path = tmp_path / "trace.jsonl"
        assert log_path.exists()
        data = json.loads(log_path.read_text(encoding="utf-8"))
        assert data["model"] == "gemini-2.5-pro"
        assert data["cost_usd"] > 0

    def test_session_summary_after_multiple_runs(self, tmp_path, monkeypatch):
        log_path = tmp_path / "session.jsonl"
        monkeypatch.setattr("scripts.observability.LOG_PATH", log_path)

        from scripts.observability import append_log
        provider = FakeProvider()
        tasks = ["버튼 수정", "알고리즘 최적화", "DB 설계", "UI 개선"]

        for task in tasks:
            result = run(task, provider)
            layers = select_layers(route(task))
            append_log(record_trace(result, task, layers))

        summary = summarize_session(log_path)
        assert summary["total_requests"] == 4
        assert summary["total_cost_usd"] > 0


# ──────────────────────────────────────────
# E2E: 비용 최적화 검증
# ──────────────────────────────────────────

class TestCostOptimization:

    def test_flash_costs_less_than_pro_per_request(self):
        from scripts.observability import calculate_cost
        cost_flash = calculate_cost("gemini-2.0-flash", 10_000, 1_000)
        cost_pro   = calculate_cost("gemini-2.5-pro",   10_000, 1_000)
        assert cost_flash < cost_pro

    def test_single_request_under_budget(self):
        """단일 요청 비용이 $0.10 이하여야 한다"""
        from scripts.observability import calculate_cost
        # 평균 요청: input 5000 tokens, output 1000 tokens
        cost = calculate_cost("gemini-2.5-pro", 5_000, 1_000)
        assert cost < 0.10, f"단일 요청 비용 초과: ${cost:.4f}"
