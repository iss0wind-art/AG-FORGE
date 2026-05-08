"""
GroqProvider 테스트 — test_groq_provider.py
FakeHTTP로 실제 Groq 호출 없이 검증한다.
"""
from __future__ import annotations
import pytest
from scripts.brain_loader import GroqProvider, BrainResponse


class FakeResponse:
    def __init__(self, data: dict, status: int = 200):
        self._data = data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._data


_FAKE_RESP = {
    "choices": [{"message": {"content": "Groq 응답입니다. 이것은 충분히 긴 응답입니다."}}],
    "usage": {"total_tokens": 42},
}


class TestGroqProvider:

    def test_init_requires_api_key(self):
        with pytest.raises(ValueError):
            GroqProvider("")

    def test_generate_returns_brain_response(self, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: FakeResponse(_FAKE_RESP))
        p = GroqProvider("test-key")
        result = p.generate("sys", ["ctx"], "작업", "llama-3.3-70b-versatile", 1000)
        assert isinstance(result, BrainResponse)

    def test_generate_text_content(self, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: FakeResponse(_FAKE_RESP))
        p = GroqProvider("test-key")
        result = p.generate("sys", [], "작업", "llama-3.3-70b-versatile", 500)
        assert "Groq" in result.text

    def test_generate_tokens_used(self, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: FakeResponse(_FAKE_RESP))
        p = GroqProvider("test-key")
        result = p.generate("sys", [], "작업", "llama-3.3-70b-versatile", 500)
        assert result.tokens_used == 42

    def test_generate_model_name(self, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: FakeResponse(_FAKE_RESP))
        p = GroqProvider("test-key")
        result = p.generate("sys", [], "작업", "llama-3.3-70b-versatile", 500)
        assert result.model == "llama-3.3-70b-versatile"

    def test_generate_task_type_groq(self, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: FakeResponse(_FAKE_RESP))
        p = GroqProvider("test-key")
        result = p.generate("sys", [], "작업", "llama-3.3-70b-versatile", 500)
        assert result.task_type == "groq"

    def test_http_error_raises(self, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: FakeResponse({}, 429))
        p = GroqProvider("test-key")
        with pytest.raises(Exception):
            p.generate("sys", [], "작업", "llama-3.3-70b-versatile", 500)

    def test_build_provider_uses_groq_when_no_gemini_deepseek(self, monkeypatch):
        import mcp_server
        from scripts.brain_loader import ChainedProvider
        monkeypatch.setenv("CLAUDE_API_KEY", "")
        monkeypatch.setenv("QWEN_API_KEY", "")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
        provider = mcp_server._build_provider()
        # ChainedProvider가 반환되며 첫 번째 프로바이더가 GroqProvider여야 함
        assert isinstance(provider, ChainedProvider)
        assert isinstance(provider._providers[0], GroqProvider)
