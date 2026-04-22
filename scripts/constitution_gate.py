"""
헌법 게이트웨이 — constitution_gate.py
모든 AI 출력이 CONSTITUTION.md의 홍익인간 0원칙을 통과해야 한다.
LLM-as-a-judge 방식으로 자동 심사한다.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

CONSTITUTION_PATH = Path(__file__).parent.parent / "CONSTITUTION.md"


@dataclass
class GateResult:
    passed: bool
    reason: str
    original_output: str
    safe_output: str


Judge = Callable[[str, str, str], bool]


def load_constitution() -> str:
    """CONSTITUTION.md를 읽어 반환한다."""
    return CONSTITUTION_PATH.read_text(encoding="utf-8")


def evaluate(output: str, task: str, judge: Judge) -> GateResult:
    """AI 출력을 헌법에 비추어 심사한다."""
    constitution = load_constitution()
    passed = judge(constitution, output, task)

    if passed:
        return GateResult(
            passed=True,
            reason="홍익인간 원칙 준수 확인",
            original_output=output,
            safe_output=output,
        )
    return GateResult(
        passed=False,
        reason="홍익인간 0원칙 위반 감지 — 응답 차단",
        original_output=output,
        safe_output="",
    )


def gate(
    output: str,
    task: str,
    judge: Judge,
    fallback_message: str = "[헌법 위반으로 응답이 차단되었습니다.]",
) -> str:
    """헌법 게이트 미들웨어 진입점."""
    result = evaluate(output, task, judge)
    return result.safe_output if result.passed else fallback_message
