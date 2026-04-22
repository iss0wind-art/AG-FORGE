"""
judgment_node + brain_accumulator 테스트
"""
from __future__ import annotations
import pytest
from pathlib import Path
from scripts.brain_loader import BrainResponse
from scripts.agent_state import AgentState


def _make_state(tmp_path: Path, **kwargs) -> AgentState:
    response = BrainResponse(
        text="충분히 긴 응답입니다. 테스트용입니다.",
        model="deepseek-chat",
        task_type="code",
        tokens_used=100,
        cache_hit=False,
    )
    base: AgentState = {
        "task": "테스트 작업",
        "decision": None,
        "current_response": response,
        "attempts": 1,
        "quality_passed": True,
        "constitution_passed": True,
        "final_response": response,
        "error": None,
        "tool_results": [],
    }
    return {**base, **kwargs}


class TestJudgmentNode:

    def test_writes_to_judgment_md(self, tmp_path, monkeypatch):
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "BRAIN_ROOT", tmp_path)
        state = _make_state(tmp_path)
        nodes.judgment_node(state)
        judgment_path = tmp_path / "judgment.md"
        assert judgment_path.exists()

    def test_judgment_contains_model(self, tmp_path, monkeypatch):
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "BRAIN_ROOT", tmp_path)
        state = _make_state(tmp_path)
        nodes.judgment_node(state)
        content = (tmp_path / "judgment.md").read_text(encoding="utf-8")
        assert "deepseek-chat" in content

    def test_judgment_contains_date(self, tmp_path, monkeypatch):
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "BRAIN_ROOT", tmp_path)
        state = _make_state(tmp_path)
        nodes.judgment_node(state)
        content = (tmp_path / "judgment.md").read_text(encoding="utf-8")
        assert "2026" in content

    def test_judgment_appends_on_multiple_calls(self, tmp_path, monkeypatch):
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "BRAIN_ROOT", tmp_path)
        state = _make_state(tmp_path)
        nodes.judgment_node(state)
        nodes.judgment_node(state)
        content = (tmp_path / "judgment.md").read_text(encoding="utf-8")
        assert content.count("deepseek-chat") == 2

    def test_judgment_returns_dict(self, tmp_path, monkeypatch):
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "BRAIN_ROOT", tmp_path)
        state = _make_state(tmp_path)
        result = nodes.judgment_node(state)
        assert isinstance(result, dict)

    def test_judgment_no_response_no_crash(self, tmp_path, monkeypatch):
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "BRAIN_ROOT", tmp_path)
        state = _make_state(tmp_path, current_response=None)
        result = nodes.judgment_node(state)
        assert isinstance(result, dict)


class TestAccumulateNode:

    def test_accumulate_appends_to_brain_md(self, tmp_path, monkeypatch):
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "BRAIN_ROOT", tmp_path)
        (tmp_path / "brain.md").write_text("# brain\n", encoding="utf-8")
        state = _make_state(tmp_path)
        nodes.accumulate_node(state)
        content = (tmp_path / "brain.md").read_text(encoding="utf-8")
        assert "테스트 작업" in content

    def test_accumulate_returns_dict(self, tmp_path, monkeypatch):
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "BRAIN_ROOT", tmp_path)
        (tmp_path / "brain.md").write_text("# brain\n", encoding="utf-8")
        state = _make_state(tmp_path)
        result = nodes.accumulate_node(state)
        assert isinstance(result, dict)

    def test_accumulate_no_brain_md_creates_it(self, tmp_path, monkeypatch):
        import scripts.agent_nodes as nodes
        monkeypatch.setattr(nodes, "BRAIN_ROOT", tmp_path)
        state = _make_state(tmp_path)
        nodes.accumulate_node(state)
        assert (tmp_path / "brain.md").exists()
