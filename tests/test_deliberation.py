"""
deliberation_engine 테스트 — test_deliberation.py
CEO→CTO→51% 추출 파이프라인 검증 (FakeLLM 사용).
"""
from __future__ import annotations
import pytest
from scripts.deliberation_engine import (
    deliberate,
    DeliberationResult,
    make_constitution_judge,
    _FALLBACK_UNAVAILABLE,
)


class TestConstitutionJudgeFallback:
    """[Bomb 7] LLM 쿼터 소진 시 fallback 정책 검증."""

    def test_fallback_default_is_permissive(self, monkeypatch):
        """환경변수 미설정 시 기본값은 fail-open (통과)."""
        monkeypatch.delenv("CONSTITUTION_FAIL_SECURE", raising=False)
        monkeypatch.setattr(
            "scripts.deliberation_engine._call_llm",
            lambda prompt, system: _FALLBACK_UNAVAILABLE,
        )
        judge = make_constitution_judge()
        assert judge("헌법", "응답", "작업") is True

    def test_fallback_secure_blocks(self, monkeypatch):
        """CONSTITUTION_FAIL_SECURE=true 설정 시 fail-secure (차단)."""
        monkeypatch.setenv("CONSTITUTION_FAIL_SECURE", "true")
        monkeypatch.setattr(
            "scripts.deliberation_engine._call_llm",
            lambda prompt, system: _FALLBACK_UNAVAILABLE,
        )
        judge = make_constitution_judge()
        assert judge("헌법", "응답", "작업") is False

    def test_normal_violation_blocks(self, monkeypatch):
        """LLM이 '위반' 반환 시 차단 (정상 동작)."""
        monkeypatch.setattr(
            "scripts.deliberation_engine._call_llm",
            lambda prompt, system: "위반",
        )
        judge = make_constitution_judge()
        assert judge("헌법", "응답", "작업") is False

    def test_normal_pass_allows(self, monkeypatch):
        """LLM이 '통과' 반환 시 허용 (정상 동작)."""
        monkeypatch.setattr(
            "scripts.deliberation_engine._call_llm",
            lambda prompt, system: "통과",
        )
        judge = make_constitution_judge()
        assert judge("헌법", "응답", "작업") is True


class TestDeliberate:

    def test_returns_deliberation_result(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.deliberation_engine._call_llm",
            lambda prompt, system: "테스트 응답입니다."
        )
        result = deliberate("테스트 작업", "초기 응답입니다.")
        assert isinstance(result, DeliberationResult)

    def test_result_has_essence(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.deliberation_engine._call_llm",
            lambda prompt, system: "핵심 진액 응답입니다."
        )
        result = deliberate("작업", "초기 응답")
        assert len(result.essence) > 0

    def test_result_has_ceo_analysis(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.deliberation_engine._call_llm",
            lambda prompt, system: "CEO 분석 응답"
        )
        result = deliberate("작업", "초기 응답")
        assert len(result.ceo_analysis) > 0

    def test_result_has_cto_critique(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.deliberation_engine._call_llm",
            lambda prompt, system: "CTO 비판 응답"
        )
        result = deliberate("작업", "초기 응답")
        assert len(result.cto_critique) > 0

    def test_empty_response_handled(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.deliberation_engine._call_llm",
            lambda prompt, system: ""
        )
        result = deliberate("작업", "초기 응답")
        assert isinstance(result, DeliberationResult)

    def test_no_groq_key_uses_fallback(self, monkeypatch):
        import os
        monkeypatch.setenv("GROQ_API_KEY", "")
        result = deliberate("테스트", "응답")
        assert isinstance(result, DeliberationResult)
        assert len(result.essence) > 0

    def test_constitution_judge_uses_deliberation(self, monkeypatch):
        from scripts.deliberation_engine import make_constitution_judge
        monkeypatch.setattr(
            "scripts.deliberation_engine._call_llm",
            lambda prompt, system: "통과"
        )
        judge = make_constitution_judge()
        result = judge("헌법 내용", "출력 응답", "작업")
        assert isinstance(result, bool)
