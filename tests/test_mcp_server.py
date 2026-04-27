"""
MCP 서버 테스트 — test_mcp_server.py
FakeProvider로 실제 Gemini 호출 없이 3개 툴을 검증한다.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

_FORGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_FORGE_ROOT))

from scripts.brain_loader import BrainResponse, LLMProvider


class FakeProvider(LLMProvider):
    def generate(self, system_instruction, context_layers, task, model, thinking_budget):
        return BrainResponse(
            text="충분히 긴 응답입니다. 이 응답은 품질 체크를 통과하기 위해 51자 이상입니다.",
            model=model,
            task_type="code",
            tokens_used=100,
            cache_hit=False,
        )


class TestAskBrain:

    @pytest.fixture(autouse=True)
    def patch_provider(self, monkeypatch):
        import mcp_server
        monkeypatch.setattr(mcp_server, "_build_provider", lambda: FakeProvider())

    def test_returns_string(self):
        from mcp_server import physis
        result = physis("코드 리뷰해줘")
        assert isinstance(result, str)

    def test_returns_non_empty(self):
        from mcp_server import physis
        result = physis("아키텍처 설계")
        assert len(result) > 0

    def test_empty_task_returns_error(self):
        from mcp_server import physis
        result = physis("   ")
        assert "오류" in result

    def test_exception_returns_error_string(self, monkeypatch):
        import mcp_server
        monkeypatch.setattr(mcp_server, "run", lambda t, p: (_ for _ in ()).throw(RuntimeError("API 실패")))
        from mcp_server import physis
        result = physis("테스트")
        assert "오류" in result or "AG-Forge" in result


class TestGetBrainStatus:

    def test_returns_dict(self):
        from mcp_server import physis_status
        result = physis_status()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        from mcp_server import physis_status
        result = physis_status()
        assert "brain_summary" in result
        assert "active_layer" in result
        assert "last_routing" in result

    def test_brain_summary_not_empty(self):
        from mcp_server import physis_status
        result = physis_status()
        assert len(result["brain_summary"]) > 0

    def test_missing_brain_md_graceful(self, tmp_path, monkeypatch):
        import mcp_server
        monkeypatch.setattr(mcp_server, "BRAIN_ROOT", tmp_path)
        result = mcp_server.physis_status()
        assert "brain.md 없음" in result["brain_summary"]


class TestGetBrainLogs:

    def test_returns_dict(self):
        from mcp_server import physis_logs
        result = physis_logs()
        assert isinstance(result, dict)

    def test_has_summary_fields(self):
        from mcp_server import physis_logs
        result = physis_logs()
        assert "total_requests" in result
        assert "total_cost_usd" in result
        assert "cache_hit_rate" in result

    def test_empty_log_returns_zeros(self, tmp_path, monkeypatch):
        import mcp_server
        monkeypatch.setattr(mcp_server, "LOG_PATH", tmp_path / "empty.jsonl")
        result = mcp_server.physis_logs()
        assert result["total_requests"] == 0


class TestFallbackProvider:

    def test_fallback_returns_brain_response(self):
        from mcp_server import _FallbackProvider
        p = _FallbackProvider()
        result = p.generate("sys", [], "테스트", "gemini-2.5-pro", 1000)
        assert isinstance(result, BrainResponse)
        assert len(result.text) > 0

    def test_fallback_contains_task(self):
        from mcp_server import _FallbackProvider
        p = _FallbackProvider()
        result = p.generate("sys", [], "특정 작업", "gemini-2.0-flash", 500)
        assert "특정 작업" in result.text


class TestPhysisEscalateDangun:
    """[다리 B] 피지수 → 본영 단군 escalation MCP 도구."""

    def test_empty_issue_returns_error(self):
        from mcp_server import physis_escalate_dangun
        result = physis_escalate_dangun(issue="", urgency="high")
        assert result["status"] == "error"

    def test_invalid_urgency_returns_error(self):
        from mcp_server import physis_escalate_dangun
        result = physis_escalate_dangun(issue="문제", urgency="critical")
        assert result["status"] == "error"
        assert "urgency" in result["message"]

    def test_normal_urgency_paperclip_not_running_error(self):
        """paperclip 미가동 시 normal urgency는 명확 에러 (silent failure 방지)."""
        from mcp_server import physis_escalate_dangun
        result = physis_escalate_dangun(issue="장기 사안", urgency="normal")
        assert result["status"] == "error"
        assert "paperclip" in result["message"]

    def test_high_urgency_escalated_to_dangun(self):
        """high urgency → 단군 호출 후 escalated 반환."""
        from unittest.mock import patch
        from mcp_server import physis_escalate_dangun
        with patch("mcp_server._call_dangun_brain", return_value="단군 응답"):
            result = physis_escalate_dangun(
                issue="4 페르소나 합의 실패",
                urgency="high",
                context={"deadlock_personas": ["공무부장", "디자이너"]},
            )
        assert result["status"] == "escalated"
        assert result["urgency"] == "high"
        assert result["timeout_sec"] == 120
        assert result["context"]["deadlock_personas"] == ["공무부장", "디자이너"]
        assert result["dangun_response"] == "단군 응답"

    def test_emergency_urgency_30s_timeout(self):
        """emergency는 30초 timeout."""
        from unittest.mock import patch
        from mcp_server import physis_escalate_dangun
        with patch("mcp_server._call_dangun_brain", return_value="단군 응답"):
            result = physis_escalate_dangun(issue="0원칙 위배 가능성", urgency="emergency")
        assert result["status"] == "escalated"
        assert result["timeout_sec"] == 30

    def test_default_context_is_dict(self):
        """context 기본값은 dict (None 처리 안전)."""
        from mcp_server import physis_escalate_dangun
        result = physis_escalate_dangun(issue="문제", urgency="high")
        assert isinstance(result["context"], dict)
