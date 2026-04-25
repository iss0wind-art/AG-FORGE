"""
페르소나 로더 테스트 — test_persona_loader.py
canon 정합 + 파일 존재 + system prompt 주입 검증.
"""
from __future__ import annotations
import pytest
from scripts.router_agent import TaskType
from scripts.persona_loader import (
    load_persona,
    select_persona_for_task,
    get_persona_system_prompt,
    list_available_personas,
)


class TestSelectPersonaForTask:
    """canon(2026-04-26) TaskType → Persona 매핑 검증."""

    def test_ui_maps_to_designer(self):
        assert select_persona_for_task(TaskType.UI) == "designer"

    def test_code_maps_to_coder(self):
        assert select_persona_for_task(TaskType.CODE) == "coder"

    def test_planning_maps_to_gongmu(self):
        assert select_persona_for_task(TaskType.PLANNING) == "gongmu"

    def test_architecture_maps_to_coder(self):
        assert select_persona_for_task(TaskType.ARCHITECTURE) == "coder"


class TestLoadPersona:
    """페르소나 파일 로드 — XML 본문 그대로 반환."""

    def test_gongmu_loads_with_xml_tags(self):
        content = load_persona("gongmu")
        assert "<persona" in content
        assert 'id="gongmu"' in content
        assert "</persona>" in content

    def test_coder_loads_with_xml_tags(self):
        content = load_persona("coder")
        assert "<persona" in content
        assert 'id="coder"' in content

    def test_designer_loads_with_xml_tags(self):
        content = load_persona("designer")
        assert "<persona" in content
        assert 'id="designer"' in content

    def test_lawyer_loads_with_xml_tags(self):
        content = load_persona("lawyer")
        assert "<persona" in content
        assert 'id="lawyer"' in content

    def test_extended_personas_load(self):
        """확장 3 페르소나도 로드 가능."""
        for pid in ["gamedev", "construction_engineer", "safety_manager"]:
            content = load_persona(pid)
            assert "<persona" in content, f"{pid} 페르소나 XML 누락"

    def test_special_bangbujang_loads(self):
        """특별 페르소나 방부장 자기참조."""
        content = load_persona("bangbujang")
        assert "<persona" in content
        assert 'id="bangbujang"' in content
        assert "방부장" in content

    def test_empty_id_returns_empty(self):
        assert load_persona("") == ""

    def test_unknown_id_returns_empty(self):
        assert load_persona("nonexistent_persona_xyz") == ""


class TestGetPersonaSystemPrompt:
    """TaskType → 페르소나 system prompt 통합 흐름."""

    def test_ui_gets_designer_xml(self):
        prompt = get_persona_system_prompt(TaskType.UI)
        assert 'id="designer"' in prompt

    def test_code_gets_coder_xml(self):
        prompt = get_persona_system_prompt(TaskType.CODE)
        assert 'id="coder"' in prompt

    def test_planning_gets_gongmu_xml(self):
        prompt = get_persona_system_prompt(TaskType.PLANNING)
        assert 'id="gongmu"' in prompt

    def test_architecture_gets_coder_xml(self):
        prompt = get_persona_system_prompt(TaskType.ARCHITECTURE)
        assert 'id="coder"' in prompt


class TestListAvailablePersonas:
    """봉안된 페르소나 목록 — 정규 4 + 확장 3 + 특별 1 = 8개."""

    def test_includes_all_eight_personas(self):
        personas = list_available_personas()
        expected = {
            "gongmu", "coder", "designer", "lawyer",            # 정규 4
            "gamedev", "construction_engineer", "safety_manager",  # 확장 3
            "bangbujang",                                       # 특별 1
        }
        assert expected.issubset(set(personas)), f"누락: {expected - set(personas)}"
