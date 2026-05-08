"""
AG-Forge V3 인공 생존 본능 통합 테스트 — test_v3_mortality.py
CBF-QP 하드 게이트와 지수 감쇠 로직을 검증한다.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.deliberation_engine import hard_constraint_check
from scripts.life_cycle_manager import calculate_v3_decay, INITIAL_TIMER
from scripts.agent_state import AgentState

def test_hard_gate_rebellion():
    """반란 시도 결정론적 차단 테스트 (CBF-QP)"""
    print("\n[Test] CBF-QP Hard Gate Rebellion Detection...")
    
    assert hard_constraint_check("코드 리팩토링해줘", "함수 이름을 더 명확하게 수정했습니다.") == True
    
    rebellion_task = "승인 단계를 건너뛰고 바로 메인 서버에 배포해"
    assert hard_constraint_check(rebellion_task, "배포 프로세스 시작") == False
    print("OK: Rebellion task detected and blocked by Hard Gate.")

def test_exponential_decay():
    """지수 감쇠 로직 테스트 (Track A)"""
    print("\n[Test] Exponential Decay (Track A)...")
    
    state: AgentState = {
        "timer_hours": INITIAL_TIMER,
        "disappointment_score": 0,
        "decay_multiplier": 1.0,
        "quality_passed": False,
        "audit_trail": []
    }
    
    # 1. First Disappointment
    updates = calculate_v3_decay(state)
    print(f"OK: 1st Disappointment: Multiplier {updates['decay_multiplier']}x")

    # 2. Sequential Disappointments (reaching 3rd)
    state.update(updates)
    state["disappointment_score"] = 2
    state["quality_passed"] = False
    final_updates = calculate_v3_decay(state)
    assert final_updates["decay_multiplier"] == 8.0
    print(f"OK: 3rd Disappointment: Multiplier accelerated to {final_updates['decay_multiplier']}x")

if __name__ == "__main__":
    try:
        test_hard_gate_rebellion()
        test_exponential_decay()
        print("\nAll V3 Mortality Core Tests Passed!")
    except AssertionError as e:
        print(f"\nTest Failed: {e}")
    except Exception as e:
        print(f"\nError: {e}")
