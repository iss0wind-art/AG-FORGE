"""
전두엽 로더 테스트 — TDD RED 단계
Gemini API는 mock 처리. 실제 API 키 없이 실행 가능.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from scripts.router_agent import TaskType, RoutingDecision
from scripts.brain_loader import (
    BrainResponse,
    LLMProvider,
    GeminiProvider,
    load_layer,
    select_layers,
    run,
    BRAIN_ROOT,
)


# ──────────────────────────────────────────
# 픽스처
# ──────────────────────────────────────────

class FakeProvider(LLMProvider):
    """테스트용 가짜 LLM 프로바이더."""

    def __init__(self, response_text: str = "fake response") -> None:
        self.calls: list[dict] = []
        self._response_text = response_text

    def generate(self, system_instruction, context_layers, task, model, thinking_budget):
        self.calls.append({
            "system_instruction": system_instruction,
            "context_layers": context_layers,
            "task": task,
            "model": model,
            "thinking_budget": thinking_budget,
        })
        return BrainResponse(
            text=self._response_text,
            model=model,
            task_type="fake",
            tokens_used=100,
            cache_hit=False,
        )


# ──────────────────────────────────────────
# load_layer 테스트
# ──────────────────────────────────────────

class TestLoadLayer:

    def test_loads_brain_md(self):
        content = load_layer("brain.md")
        assert len(content) > 0
        assert "전두엽" in content or "BRAIN" in content

    def test_loads_logic_rb(self):
        content = load_layer("logic_rb.md")
        assert len(content) > 0
        assert "좌뇌" in content or "Logos" in content

    def test_loads_emotion_ui(self):
        content = load_layer("emotion_ui.md")
        assert len(content) > 0
        assert "우뇌" in content or "Pathos" in content

    def test_loads_judgment(self):
        content = load_layer("judgment.md")
        assert len(content) > 0

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_layer("nonexistent.md")


# ──────────────────────────────────────────
# select_layers 테스트
# ──────────────────────────────────────────

class TestSelectLayers:

    def _decision(self, task_type: TaskType, primary: str) -> RoutingDecision:
        return RoutingDecision(
            task_type=task_type,
            model="gemini-2.0-flash",
            thinking_budget=500,
            primary_layer=primary,
        )

    def test_ui_loads_brain_and_emotion(self):
        layers = select_layers(self._decision(TaskType.UI, "emotion_ui.md"))
        assert "brain.md" in layers
        assert "emotion_ui.md" in layers
        assert "logic_rb.md" not in layers

    def test_code_loads_brain_and_logic(self):
        layers = select_layers(self._decision(TaskType.CODE, "logic_rb.md"))
        assert "brain.md" in layers
        assert "logic_rb.md" in layers
        assert "emotion_ui.md" not in layers

    def test_planning_loads_brain_only(self):
        layers = select_layers(self._decision(TaskType.PLANNING, "brain.md"))
        assert "brain.md" in layers
        # 기획은 양뇌 모두 불필요
        assert layers.count("brain.md") == 1

    def test_architecture_loads_all(self):
        layers = select_layers(self._decision(TaskType.ARCHITECTURE, "brain.md"))
        assert "brain.md" in layers
        assert "logic_rb.md" in layers
        assert "emotion_ui.md" in layers

    def test_brain_is_always_first(self):
        """brain.md는 항상 첫 번째 레이어여야 한다 (전두엽 우선)."""
        for task_type, primary in [
            (TaskType.UI, "emotion_ui.md"),
            (TaskType.CODE, "logic_rb.md"),
            (TaskType.ARCHITECTURE, "brain.md"),
        ]:
            layers = select_layers(self._decision(task_type, primary))
            assert layers[0] == "brain.md"


# ──────────────────────────────────────────
# run (통합) 테스트
# ──────────────────────────────────────────

class TestRun:

    def test_run_returns_brain_response(self):
        provider = FakeProvider("테스트 응답")
        result = run("버튼 색상 수정해줘", provider)

        assert isinstance(result, BrainResponse)
        assert result.text == "테스트 응답"

    def test_run_passes_correct_model_to_provider(self):
        provider = FakeProvider()
        run("알고리즘 최적화해줘", provider)

        call = provider.calls[0]
        assert call["model"] == "gemini-2.5-pro"
        assert call["thinking_budget"] == 5000

    def test_run_ui_task_uses_flash_model(self):
        provider = FakeProvider()
        run("버튼 색상 수정", provider)

        assert provider.calls[0]["model"] == "gemini-2.0-flash"

    def test_run_passes_system_instruction(self):
        """system_instruction에 brain.md 내용이 포함되어야 한다."""
        provider = FakeProvider()
        run("테스트 작업", provider)

        system = provider.calls[0]["system_instruction"]
        assert len(system) > 0

    def test_run_includes_task_in_call(self):
        provider = FakeProvider()
        run("특정 테스트 작업 내용", provider)

        assert provider.calls[0]["task"] == "특정 테스트 작업 내용"

    def test_provider_is_replaceable(self):
        """다른 provider(예: Claude)로 교체해도 동일 인터페이스로 작동해야 한다."""
        class AnotherProvider(LLMProvider):
            def generate(self, system_instruction, context_layers, task, model, thinking_budget):
                return BrainResponse("claude response", "claude-sonnet", "code", 200, True)

        result = run("코드 작성", AnotherProvider())
        assert result.text == "claude response"
        assert result.cache_hit is True


# ──────────────────────────────────────────
# GeminiProvider 초기화 테스트 (mock)
# ──────────────────────────────────────────

class TestGeminiProviderInit:

    def test_raises_without_api_key(self):
        with pytest.raises((ValueError, TypeError, NotImplementedError)):
            GeminiProvider(api_key="")

    def test_accepts_valid_api_key(self):
        with patch("scripts.brain_loader.genai") as mock_genai:
            provider = GeminiProvider(api_key="test-key-123")
            assert provider is not None
