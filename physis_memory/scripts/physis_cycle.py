"""
피지수 사이클 — 세션 종료 시 실행
1. 이천 CAD 파싱 (신규 .fcstd/.step → wiki 노트)
2. CMA Layer 0/1 게이트 심사
3. CMA Layer 2 LLM 심사 (의심 노트만)
4. 소급 평가 (ref_count, outcome_score 갱신)
5. 망각/승격 실행
6. Graphify 그래프 업데이트
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


def run_cad_parser():
    print(f"\n{'='*40}\n[이천 CAD 파싱]")
    result = subprocess.run(
        [sys.executable, "/home/nas/FreeCAD_4TH/scripts/cad_to_wiki.py"],
        capture_output=False
    )
    return result.returncode == 0


if __name__ == "__main__":
    print("🧠 피지수 사이클 시작")
    run_cad_parser()
    run("CMA Layer0/1 심사", "cma_gate.py")
    run("CMA Layer2 LLM 심사", "cma_layer2.py")
    run("소급 평가", "memory_promotion.py")
    run("망각·승격", "forgetting_manager.py")
    update_graph()
    print("\n✅ 피지수 사이클 완료")
