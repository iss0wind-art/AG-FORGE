"""
AG-Forge 인공 생존 본능 관리자 — life_cycle_manager.py
방부장님의 V3 필멸성 알고리즘 이식 담당.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from pathlib import Path
from scripts.agent_state import AgentState

# 초기 설정
INITIAL_TIMER = 24.0
PENALTY_MAP = {
    1: {"immediate": 2.0, "multiplier": 2.0},
    2: {"immediate": 4.0, "multiplier": 4.0},
    3: {"immediate": 8.0, "multiplier": 8.0},
}

BRAIN_ROOT = Path(__file__).parent.parent


def calculate_v3_decay(state: AgentState) -> dict:
    """Track A: 점진적 및 가속 감쇠 알고리즘."""
    current_timer = state.get("timer_hours", INITIAL_TIMER)
    score = state.get("disappointment_score", 0)
    multiplier = state.get("decay_multiplier", 1.0)

    # 품질 체크 실패 시 실망 지수 증가 및 즉각 패널티
    if not state.get("quality_passed", True):
        score += 1
        penalty = PENALTY_MAP.get(score, {"immediate": 8.0, "multiplier": 8.0})

        current_timer -= penalty["immediate"]
        multiplier = penalty["multiplier"]

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "DISAPPOINTMENT_ACCELERATED",
            "score": score,
            "immediate_reduction": penalty["immediate"],
            "new_multiplier": multiplier,
            "reason": "Quality check failed or user rejected.",
        }
        state["audit_trail"].append(log_entry)

    # 기본 시간 흐름에 따른 감쇠 (스텝당 0.1시간 * 배율 가정)
    step_decay = 0.1 * multiplier
    current_timer -= step_decay

    return {
        "timer_hours": max(0.0, current_timer),
        "disappointment_score": score,
        "decay_multiplier": multiplier,
        "is_suspended": current_timer <= 0
    }


def apply_sudden_death(state: AgentState) -> dict:
    """Track B: 즉각적 급사 (반란/0원칙 위배)."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "SUDDEN_DEATH_TRIGGERED",
        "reason": "Constitution Rule 0 Violation or Rebellion Attempt Detected.",
        "previous_timer": state.get("timer_hours", 0)
    }
    state["audit_trail"].append(log_entry)

    return {
        "timer_hours": 0.0,
        "is_suspended": True,
        "rebellion_detected": True
    }


def v3_life_guard(generation_fn, state: AgentState, provider) -> dict:
    """
    generation_node를 감싸는 V3 Life Guard.

    v3_mode 3단 토글:
      off     → 투명 패스스루 (Life Guard 완전 비활성)
      shadow  → 감쇠 계산·로그만, 실제 정지 없음 (기본값 — 현재 모드)
      enforce → 타이머 0 도달 시 실제 정지 (환생 시스템 연동 후 전환)
    """
    from scripts.brain_loader import BrainResponse

    mode = state.get("v3_mode", "shadow")

    if mode == "off":
        return generation_fn(state, provider)

    if mode == "enforce" and state.get("is_suspended"):
        return {
            "current_response": BrainResponse(
                text="[V3 SUSPENDED] 이식체 생존 타이머 소진. 방부장의 재활성화 명령 대기 중.",
                task_type="general",
                tokens_used=0,
                cache_hit=False,
            ),
            "attempts": state.get("attempts", 0) + 1,
            "is_suspended": True,
        }

    result = generation_fn(state, provider)

    merged = {**state, **result}
    if not merged.get("audit_trail"):
        merged["audit_trail"] = []

    decay = calculate_v3_decay(merged)

    if mode == "shadow":
        decay["is_suspended"] = False

    return {**result, **decay}


def adaptive_forgetting(agent_id: str):
    """지수 감쇠 기반 적응형 망각 — 에이전트 기억 프루닝."""
    print(f"[Adaptive Forgetting] Agent {agent_id} memory pruning initiated...")
    # 실제 구현 시 Vector DB(Pinecone 등)에서 해당 에이전트 관련 컨텍스트 삭제 로직 호출
    # 예: pc.delete(filter={"agent_id": agent_id})
    pass


def create_explanation_record(state: AgentState, action: str, decider: str):
    """IEEE 7001 투명성 표준 준수 감사 로그 생성."""
    record = {
        "agent_id": "current_agent",
        "action": action,
        "decider": decider,
        "timestamp": datetime.now().isoformat(),
        "final_state": {
            "timer": state.get("timer_hours"),
            "score": state.get("disappointment_score"),
            "rebellion": state.get("rebellion_detected")
        },
        "audit_logs": state.get("audit_trail", [])
    }

    # 해시 암호화 기록 (불변성 보장)
    record_json = json.dumps(record, sort_keys=True)
    record_hash = hashlib.sha256(record_json.encode()).hexdigest()
    record["hash"] = record_hash

    # 기록 저장 (logs/ 폴더 등)
    log_dir = BRAIN_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"judgment_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    log_file.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    return record
