"""
deliberation_engine 테스트 — test_deliberation.py
CEO→CTO→51% 추출 파이프라인 검증 (FakeLLM 사용).
"""
from __future__ import annotations
import pytest
from scripts.deliberation_engine import deliberate, DeliberationResult


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
