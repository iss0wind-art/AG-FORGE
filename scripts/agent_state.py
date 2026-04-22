"""
AG-Forge LangGraph 상태 스키마 — agent_state.py
모든 그래프 노드가 공유하는 불변 상태 구조.
"""
from __future__ import annotations
from typing import Annotated
import operator
from typing_extensions import TypedDict

from scripts.brain_loader import BrainResponse
from scripts.router_agent import RoutingDecision

MAX_ATTEMPTS = 3


class AgentState(TypedDict):
    task: str                                          # 원본 사용자 입력 (불변)
    decision: RoutingDecision | None                   # 소뇌 라우팅 결과
    current_response: BrainResponse | None             # 현재 시도 응답
    attempts: int                                      # 시도 횟수 (circuit breaker)
    quality_passed: bool                               # 자가 검증 통과 여부
    constitution_passed: bool                          # 헌법 게이트 통과 여부
    final_response: BrainResponse | None               # 최종 확정 응답
    error: str | None                                  # 오류 메시지
    tool_results: Annotated[list[str], operator.add]   # 툴 결과 누적
