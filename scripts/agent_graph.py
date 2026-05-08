"""
AG-Forge LangGraph 그래프 조립 — agent_graph.py
조건부 순환 그래프로 자율 에이전트 루프를 구현한다.
"""
from __future__ import annotations
from langgraph.graph import StateGraph, END

from scripts.brain_loader import LLMProvider
from scripts.agent_state import AgentState, MAX_ATTEMPTS
from scripts.agent_nodes import (
    routing_node,
    generation_node,
    quality_check_node,
    tool_node,
    constitution_node,
    judgment_node,
    accumulate_node,
)
from scripts.life_cycle_manager import v3_life_guard


def _route_after_generation(state: AgentState) -> str:
    """generation 이후 V3 enforce 모드 정지 여부 분기."""
    if state.get("is_suspended") and state.get("v3_mode") == "enforce":
        return "suspended"
    return "quality_check"


def _route_after_quality(state: AgentState) -> str:
    """quality_check 이후 분기 결정."""
    if state["attempts"] >= MAX_ATTEMPTS:
        return "abort"
    if not state["quality_passed"]:
        return "retry"
    return "ok"


def _route_after_constitution(state: AgentState) -> str:
    """constitution 이후 분기 결정."""
    if state["constitution_passed"]:
        return "passed"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "abort"
    return "retry"


def build_agent_graph(provider: LLMProvider):
    """LangGraph 컴파일된 그래프를 반환한다."""
    graph = StateGraph(AgentState)

    # 노드 등록
    graph.add_node("routing",       routing_node)
    graph.add_node("generation",    lambda s: v3_life_guard(generation_node, s, provider))
    graph.add_node("quality_check", quality_check_node)
    graph.add_node("tool_call",     tool_node)
    graph.add_node("constitution",  constitution_node)
    graph.add_node("judgment",      judgment_node)
    graph.add_node("accumulate",    accumulate_node)

    # 진입점
    graph.set_entry_point("routing")

    # 정적 엣지
    graph.add_edge("routing",   "generation")
    graph.add_edge("tool_call", "generation")

    # V3 Life Guard 분기: enforce 정지 시 END, 아니면 quality_check
    graph.add_conditional_edges(
        "generation",
        _route_after_generation,
        {"quality_check": "quality_check", "suspended": END},
    )
    graph.add_edge("judgment",   "accumulate")
    graph.add_edge("accumulate", END)

    # 조건부 엣지: quality_check 결과에 따라 분기
    graph.add_conditional_edges(
        "quality_check",
        _route_after_quality,
        {
            "retry":  "generation",
            "ok":     "constitution",
            "abort":  END,
        },
    )

    # 조건부 엣지: constitution 결과에 따라 분기
    graph.add_conditional_edges(
        "constitution",
        _route_after_constitution,
        {
            "passed": "judgment",
            "retry":  "generation",
            "abort":  END,
        },
    )

    return graph.compile()
