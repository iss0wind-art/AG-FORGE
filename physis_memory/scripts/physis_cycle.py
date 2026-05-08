"""
피지수 사이클 — 세션 종료 시 실행
1. CMA 게이트 심사
2. 소급 평가 (ref_count, outcome_score 갱신)
3. 망각/승격 실행
4. Graphify 그래프 업데이트
"""

import subprocess
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent
SCRIPTS = Path(__file__).parent


def run(label: str, script: str):
    print(f"\n{'='*40}\n[{label}]")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        cwd=str(SCRIPTS),
        capture_output=False
    )
    return result.returncode == 0


def update_graph():
    print(f"\n{'='*40}\n[Graphify 업데이트]")
    result = subprocess.run(
        ["graphify", "update", "."],
        cwd=str(VAULT_ROOT),
        capture_output=False
    )
    return result.returncode == 0


if __name__ == "__main__":
    print("🧠 피지수 사이클 시작")
    run("CMA 헌법 심사", "cma_gate.py")
    run("소급 평가", "memory_promotion.py")
    run("망각·승격", "forgetting_manager.py")
    update_graph()
    print("\n✅ 피지수 사이클 완료")
