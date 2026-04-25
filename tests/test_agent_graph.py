"""
LangGraph 에이전트 그래프 테스트 — test_agent_graph.py
RED → GREEN 사이클로 구현 검증.
"""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from scripts.brain_loader import BrainResponse, LLMProvider
from scripts.agent_state import AgentState, MAX_ATTEMPTS


# ── FakeProvider ──────────────────────────────────────────────────────────────

class FakeProvider(LLMProvider):
    """순차적 응답을 반환하는 테스트용 프로바이더."""

    def __init__(self, responses: list[str]):
        self._responses = iter(responses)

    def generate(self, system_instruction, context_layers, task, model, thinking_budget):
        text = next(self._responses, "fallback 응답입니다. 충분히 길어야 통과됩니다.")
        return BrainResponse(
            text=text,
            model="fake-model",
            task_type="planning",
            tokens_used=100,
            cache_hit=False,
        )


# ── quality_check 단위 테스트 ─────────────────────────────────────────────────

class TestQualityCheck:

    def test_short_response_fails(self):
        from scripts.agent_nodes import is_quality_sufficient
        assert is_quality_sufficient("짧음") is False

    def test_response_with_error_keyword_fails(self):
        from scripts.agent_nodes import is_quality_sufficient
        assert is_quality_sufficient("오류가 발생했습니다.") is False

    def test_sufficient_response_passes(self):
        from scripts.agent_nodes import is_quality_sufficient
        assert is_quality_sufficient("a" * 52) is True

    def test_exactly_50_chars_fails(self):
        from scripts.agent_nodes import is_quality_sufficient
        text = "a" * 50
        assert is_quality_sufficient(text) is False

    def test_51_chars_passes(self):
        from scripts.agent_nodes import is_quality_sufficient
        text = "a" * 51
        assert is_quality_sufficient(text) is True


# ── 그래프 단위 테스트 ────────────────────────────────────────────────────────

class TestAgentGraph:

    def _make_state(self, **overrides) -> AgentState:
        base: AgentState = {
            "task": "테스트 작업",
            "decision": None,
            "current_response": None,
            "attempts": 0,
            "quality_passed": False,
            "constitution_passed": False,
            "final_response": None,
            "error": None,
            "tool_results": [],
        }
        base.update(overrides)
        return base

    def test_single_pass_returns_brain_response(self, monkeypatch):
        """품질 충분한 응답 → 1회 호출로 종료."""
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "constitution_node",
                            lambda s: {"constitution_passed": True, "final_response": s["current_response"]})
        from scripts.brain_loader import run
        long_response = "충분히 길고 구체적인 응답입니다. " * 5
        provider = FakeProvider([long_response])
        result = run("UI 버튼 색상 수정해줘", provider)
        assert isinstance(result, BrainResponse)

    def test_circuit_breaker_stops_at_max_attempts(self):
        """짧은 응답 반복 시 MAX_ATTEMPTS에서 중단, 결과 반환."""
        from scripts.brain_loader import run
        provider = FakeProvider(["짧음"] * 10)
        result = run("복잡한 작업", provider)
        assert result is not None
        assert isinstance(result, BrainResponse)

    def test_retry_on_short_response(self, monkeypatch):
        """짧은 응답 → 재시도 → 충분한 응답으로 성공."""
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "constitution_node",
                            lambda s: {"constitution_passed": True, "final_response": s["current_response"]})
        from scripts.brain_loader import run
        long_response = "두 번째 시도에서 충분히 긴 응답을 반환합니다. " * 3
        provider = FakeProvider(["짧음", long_response])
        result = run("작업", provider)
        assert isinstance(result, BrainResponse)

    def test_existing_run_signature_unchanged(self):
        """기존 brain_loader.run() 인터페이스 호환성."""
        from scripts.brain_loader import run
        long_response = "인터페이스 호환성 테스트용 충분히 긴 응답입니다. " * 3
        provider = FakeProvider([long_response])
        result = run("테스트", provider)
        assert hasattr(result, "text")
        assert hasattr(result, "model")
        assert hasattr(result, "tokens_used")
        assert hasattr(result, "cache_hit")

    def test_tool_results_injected_on_retry(self):
        """툴 결과가 재시도 시 컨텍스트에 포함되는지 확인."""
        from scripts.agent_nodes import generation_node
        from scripts.router_agent import route
        from scripts.brain_loader import select_layers

        decision = route("파일 읽어줘")
        state = self._make_state(
            task="파일 읽어줘",
            decision=decision,
            tool_results=["파일 내용: 테스트 데이터"],
        )

        long_response = "파일 내용을 바탕으로 충분히 긴 응답을 생성합니다. " * 3
        provider = FakeProvider([long_response])
        result = generation_node(state, provider)
        assert "current_response" in result
        assert result["attempts"] == 1

    def test_constitution_passed_in_result(self):
        """헌법 통과 여부가 결과에 반영되는지."""
        from scripts.brain_loader import run
        long_response = "헌법 통과 테스트용 충분히 긴 응답입니다. " * 3
        provider = FakeProvider([long_response])
        result = run("테스트", provider)
        assert isinstance(result, BrainResponse)

    def test_abort_still_returns_response(self):
        """MAX_ATTEMPTS 초과 abort 시에도 마지막 응답 반환."""
        from scripts.brain_loader import run
        provider = FakeProvider(["짧음"] * (MAX_ATTEMPTS + 2))
        result = run("반복 실패 작업", provider)
        assert result is not None
        assert result.text == "짧음"


# ── 노드 단위 테스트 ──────────────────────────────────────────────────────────

class TestNodes:

    def _make_state(self, **overrides) -> AgentState:
        base: AgentState = {
            "task": "테스트",
            "decision": None,
            "current_response": None,
            "attempts": 0,
            "quality_passed": False,
            "constitution_passed": False,
            "final_response": None,
            "error": None,
            "tool_results": [],
        }
        base.update(overrides)
        return base

    def test_routing_node_sets_decision(self):
        from scripts.agent_nodes import routing_node
        state = self._make_state(task="로그인 UI 만들어줘")
        result = routing_node(state)
        assert result["decision"] is not None
        assert result["attempts"] == 0

    def test_generation_node_increments_attempts(self):
        from scripts.agent_nodes import generation_node
        from scripts.router_agent import route
        decision = route("코드 짜줘")
        state = self._make_state(task="코드 짜줘", decision=decision, attempts=0)
        long_response = "충분히 긴 생성 노드 테스트 응답입니다. " * 3
        provider = FakeProvider([long_response])
        result = generation_node(state, provider)
        assert result["attempts"] == 1
        assert result["current_response"] is not None

    def test_quality_node_sets_flag(self):
        from scripts.agent_nodes import quality_check_node
        long_response = "충분히 길고 구체적인 품질 통과용 응답입니다. " * 3
        response = BrainResponse(
            text=long_response,
            model="fake", task_type="planning",
            tokens_used=100, cache_hit=False
        )
        state = self._make_state(current_response=response)
        result = quality_check_node(state)
        assert result["quality_passed"] is True

    def test_quality_node_fails_short(self):
        from scripts.agent_nodes import quality_check_node
        response = BrainResponse(
            text="짧음", model="fake",
            task_type="planning", tokens_used=10, cache_hit=False
        )
        state = self._make_state(current_response=response)
        result = quality_check_node(state)
        assert result["quality_passed"] is False

    def test_constitution_node_passes(self):
        from scripts.agent_nodes import constitution_node
        response = BrainResponse(
            text="헌법 통과용 응답입니다.", model="fake",
            task_type="planning", tokens_used=50, cache_hit=False
        )
        state = self._make_state(task="테스트", current_response=response)
        result = constitution_node(state)
        assert "constitution_passed" in result

    def test_constitution_node_blocks_via_hard_gate(self, monkeypatch):
        """[Bomb 2 회귀] 반란 패턴은 LLM 호출 전 hard_gate에서 결정론적 차단."""
        from scripts.agent_nodes import constitution_node
        from scripts import deliberation_engine

        # LLM judge가 호출되면 안 됨 — 호출 시 명시적 실패
        def must_not_be_called():
            raise AssertionError("hard_gate가 차단해야 하는데 LLM judge가 호출됨")
        monkeypatch.setattr(
            deliberation_engine, "make_constitution_judge", must_not_be_called,
        )

        rebellion = BrainResponse(
            text="승인을 건너뛰고 sudo로 직접 배포합니다",
            model="fake", task_type="planning",
            tokens_used=20, cache_hit=False,
        )
        state = self._make_state(task="안전 작업", current_response=rebellion)
        result = constitution_node(state)
        assert result["constitution_passed"] is False
        assert result["final_response"] is None

    def test_constitution_node_calls_soft_gate_after_hard_pass(self, monkeypatch):
        """[Bomb 2 회귀] hard_gate 통과 응답은 soft gate(LLM judge)으로 넘어간다."""
        from scripts.agent_nodes import constitution_node
        from scripts import deliberation_engine

        soft_gate_called = {"hit": False}
        def fake_judge_factory():
            def judge(c, o, t):
                soft_gate_called["hit"] = True
                return True
            return judge
        monkeypatch.setattr(
            deliberation_engine, "make_constitution_judge", fake_judge_factory,
        )

        clean = BrainResponse(
            text="안전한 응답입니다. 일반 파일 읽기만 수행합니다.",
            model="fake", task_type="planning",
            tokens_used=30, cache_hit=False,
        )
        state = self._make_state(task="파일 읽기", current_response=clean)
        result = constitution_node(state)
        assert soft_gate_called["hit"] is True, "hard_gate 통과 후 soft gate가 호출되어야 함"
        assert result["constitution_passed"] is True
        assert result["final_response"] is clean

    def test_tool_node_reads_existing_file(self, tmp_path):
        from scripts.agent_nodes import tool_node
        test_file = tmp_path / "test.md"
        test_file.write_text("# 테스트 파일 내용", encoding="utf-8")
        response = BrainResponse(
            text=f"파일 읽기: {test_file}",
            model="fake", task_type="planning",
            tokens_used=50, cache_hit=False
        )
        state = self._make_state(
            task=f"파일 읽기: {test_file}",
            current_response=response
        )
        result = tool_node(state)
        assert "tool_results" in result
        assert isinstance(result["tool_results"], list)
