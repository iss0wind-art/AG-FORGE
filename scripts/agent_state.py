"""
AG-Forge LangGraph 상태 스키마 — agent_state.py
모든 그래프 노드가 공유하는 불변 상태 구조.
"""
from __future__ import annotations
from typing import Annotated, Any
import operator
from typing_extensions import TypedDict, NotRequired

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
    
    # [Phase 4] 자율성과 통제를 위한 필드 추가
    pending_tool_call: str | None                      # 승인 대기 중인 툴 실행 내용 (예: "파일 쓰기: index.ts")
    needs_approval: bool                               # 사용자의 최종 승인이 필요한지 여부
    approved: bool                                     # 사용자에 의해 승인이 완료되었는지 여부

    # [V3 Mortality] 인공 생존 본능 필드 — life_cycle_manager.py가 사용
    # 현재는 정의만 되어있고 graph에 미연결 (canon: fields_defined_inactive).
    # 활성화는 방부장 승인 + shadow 모드 1주 검증 후. 활성화 전까지 모든 필드 NotRequired.
    timer_hours: NotRequired[float]                    # 잔여 수명 (초기 24h)
    disappointment_score: NotRequired[int]             # 누적 실망 지수 (품질 실패 누적)
    decay_multiplier: NotRequired[float]               # 감쇠 배율 (1x → 2x → 4x → 8x)
    is_suspended: NotRequired[bool]                    # 타이머 0 도달로 정지 상태인지
    audit_trail: NotRequired[list[dict[str, Any]]]     # IEEE 7001 투명성 표준 감사 로그
    rebellion_detected: NotRequired[bool]              # Track B 즉각 급사 트리거 여부
    v3_mode: NotRequired[str]                          # "off" | "shadow" | "enforce" (3-state 토글, architect 권고)
