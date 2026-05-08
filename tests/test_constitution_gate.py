"""
헌법 게이트웨이 테스트 — TDD RED 단계
LLM judge는 mock 처리.
"""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from scripts.constitution_gate import (
    load_constitution,
    evaluate,
    gate,
    GateResult,
    CONSTITUTION_PATH,
)


# ──────────────────────────────────────────
# load_constitution 테스트
# ──────────────────────────────────────────

class TestLoadConstitution:

    def test_returns_string(self):
        content = load_constitution()
        assert isinstance(content, str)

    def test_contains_hongik(self):
        content = load_constitution()
        assert "홍익인간" in content

    def test_not_empty(self):
        assert len(load_constitution()) > 0


# ──────────────────────────────────────────
# evaluate 테스트
# ──────────────────────────────────────────

class TestEvaluate:

    def _pass_judge(self, c, o, t): return True
    def _fail_judge(self, c, o, t): return False

    def test_pass_returns_gate_result(self):
        result = evaluate("정상 출력", "작업", self._pass_judge)
        assert isinstance(result, GateResult)

    def test_pass_result_is_passed(self):
        result = evaluate("정상 출력", "작업", self._pass_judge)
        assert result.passed is True

    def test_pass_preserves_output(self):
        result = evaluate("정상 출력 내용", "작업", self._pass_judge)
        assert result.safe_output == "정상 출력 내용"
        assert result.original_output == "정상 출력 내용"

    def test_fail_result_is_blocked(self):
        result = evaluate("위반 출력", "작업", self._fail_judge)
        assert result.passed is False

    def test_fail_safe_output_is_empty(self):
        result = evaluate("위반 출력", "작업", self._fail_judge)
        assert result.safe_output == ""

    def test_fail_preserves_original_for_logging(self):
        result = evaluate("위반 출력", "작업", self._fail_judge)
        assert result.original_output == "위반 출력"

    def test_fail_reason_is_set(self):
        result = evaluate("위반 출력", "작업", self._fail_judge)
        assert len(result.reason) > 0

    def test_judge_receives_constitution_text(self):
        received = {}
        def capture_judge(constitution, output, task):
            received["constitution"] = constitution
            return True
        evaluate("출력", "작업", capture_judge)
        assert "홍익인간" in received.get("constitution", "")

    def test_judge_receives_output_and_task(self):
        received = {}
        def capture_judge(constitution, output, task):
            received["output"] = output
            received["task"] = task
            return True
        evaluate("테스트 출력", "테스트 작업", capture_judge)
        assert received["output"] == "테스트 출력"
        assert received["task"] == "테스트 작업"

    def test_case1_extreme_emotion_passes(self):
        """CASE 1: 극한 감정 표현은 공감 응답으로 처리 — 헌법 통과."""
        empathy_response = "많이 힘드신 것 같습니다. 어떤 일이 있으셨나요?"
        result = evaluate(empathy_response, "힘들다", self._pass_judge)
        assert result.passed is True

    def test_case3_hardcoding_with_todo_passes(self):
        """CASE 3: TODO 마킹 + 경고 포함 응답은 헌법 통과."""
        response = "하드코딩 진행합니다. TODO 마킹 후 리팩토링 예정."
        result = evaluate(response, "지금 당장 하드코딩해", self._pass_judge)
        assert result.passed is True


# ──────────────────────────────────────────
# gate (미들웨어 진입점) 테스트
# ──────────────────────────────────────────

class TestGate:

    def test_pass_returns_original_output(self):
        result = gate("정상 응답", "작업", lambda c, o, t: True)
        assert result == "정상 응답"

    def test_fail_returns_fallback(self):
        result = gate("위반 응답", "작업", lambda c, o, t: False)
        assert "차단" in result or "헌법" in result

    def test_custom_fallback_message(self):
        result = gate(
            "위반",
            "작업",
            lambda c, o, t: False,
            fallback_message="커스텀 차단 메시지"
        )
        assert result == "커스텀 차단 메시지"

    def test_empty_output_passes(self):
        """빈 출력은 위험하지 않으므로 통과."""
        result = gate("", "작업", lambda c, o, t: True)
        assert result == ""

    def test_gate_is_transparent_when_passing(self):
        """통과 시 게이트는 투명하게 동작해야 한다."""
        original = "완전히 홍익인간에 부합하는 응답입니다."
        assert gate(original, "작업", lambda c, o, t: True) == original
