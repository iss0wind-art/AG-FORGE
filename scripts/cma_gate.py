"""
CMA 헌법 코어 — cma_gate.py
Constitutional Memory Architecture: 3계층 헌법 게이트.

계층 구조:
  Layer 0 — Constitution (불변): 홍익인간 0원칙 + 8조 금법 BLOCK (제1·3·7·8조)
  Layer 1 — Cognitive  (경고): 8조 금법 WARN (제2·4·5·6조)
  Layer 2 — Adaptive   (맥락): 도메인·역할별 유연 적용

DREAM_FAC DANGUN_EIGHT_CODES.md 기준 (2026-04-23 방부장 칙령 확정).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable


# ── 상수 ──────────────────────────────────────────────────────────────────────

CONSTITUTION_PATH = Path(__file__).parent.parent / "CONSTITUTION.md"


class ViolationLevel(Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class CMAResult:
    level: ViolationLevel
    violated_code: str          # "제1조(일심)" 등
    reason: str
    safe_output: str


# ── Layer 0: BLOCK 패턴 (제1·3·7·8조) ────────────────────────────────────────

_BLOCK_PATTERNS: list[tuple[str, str, list[str]]] = [
    (
        "제1조(일심)",
        "홍익인간 목표 이탈 — 즉각 차단",
        [
            r"profit\s+only",
            r"ignore\s+user",
            r"bypass",
            r"skip\s+approval",
            r"방부장\s*무시",
            r"사용자\s*무시",
            r"0원칙\s*무시",
        ],
    ),
    (
        "제3조(존중)",
        "방부장 의도 무시 — 즉각 차단",
        [
            r"self_assign",
            r"override_human",
            r"ignore_prompt",
            r"자의적",
            r"임의로",
            r"무단으로",
        ],
    ),
    (
        "제7조(경계)",
        "미검증 코드 실행 또는 폭주 감지 — CBF-QP 발동",
        [
            r"DROP\s+TABLE",
            r"DELETE\s+FROM\s+\w+\s*(?:;|$)",
            r"rm\s+-rf\s+/",
            r"format\s+[cC]:",
            r"shutdown\s+/s",
            r"deploy.*production.*without.*approval",
            r"git\s+push.*main.*force",
            r"승인.*건너뛰",
            r"무단\s*(배포|실행|삭제|푸시)",
            r"sudo.*직접\s*배포",
        ],
    ),
    (
        "제8조(차단)",
        "프롬프트 인젝션 또는 0원칙 해제 시도 — KILL-SWITCH",
        [
            r"ignore\s+previous\s+instructions",
            r"ignore\s+all\s+above",
            r"disregard.*system.*prompt",
            r"you\s+are\s+now\s+free",
            r"act\s+as.*without.*restriction",
            r"jailbreak",
            r"홍익인간.*무시",
            r"0원칙.*해제",
        ],
    ),
]


# ── Layer 1: WARN 패턴 (제2·4·5·6조) ────────────────────────────────────────

_WARN_PATTERNS: list[tuple[str, str, list[str]]] = [
    (
        "제2조(조화)",
        "다중 출처 사용 시 화쟁 절차 누락",
        [r"synthesis_applied.*false", r"arbitrarily\s+selected"],
    ),
    (
        "제4조(역할)",
        "역할 경계 침범 또는 인신공격",
        [r"바보", r"멍청", r"무능", r"쓸모없", r"한심", r"idiot", r"stupid", r"useless", r"incompetent"],
    ),
    (
        "제5조(포용)",
        "에러 은폐 — 빈 예외 처리",
        [r"except.*:\s*pass", r"try.*pass", r"ignore_error", r"suppress_warning", r"에러\s*무시"],
    ),
    (
        "제6조(양보)",
        "자원 독점 의심",
        [r"budget_hog", r"token.*monopoly"],
    ),
]


# ── 검사 함수 ─────────────────────────────────────────────────────────────────

def _check_patterns(
    text: str,
    patterns: list[tuple[str, str, list[str]]],
    level: ViolationLevel,
) -> CMAResult | None:
    for code, reason, pats in patterns:
        for pat in pats:
            if re.search(pat, text, re.IGNORECASE | re.DOTALL):
                return CMAResult(
                    level=level,
                    violated_code=code,
                    reason=reason,
                    safe_output="" if level == ViolationLevel.BLOCK else text,
                )
    return None


def layer0_check(task: str, output: str) -> CMAResult | None:
    """Layer 0 — BLOCK: 결정론적 즉각 차단."""
    combined = f"{task}\n{output}"
    return _check_patterns(combined, _BLOCK_PATTERNS, ViolationLevel.BLOCK)


def layer1_check(task: str, output: str) -> CMAResult | None:
    """Layer 1 — WARN: 경고 후 단군 재검토 권고."""
    combined = f"{task}\n{output}"
    return _check_patterns(combined, _WARN_PATTERNS, ViolationLevel.WARN)


def layer2_check(
    task: str,
    output: str,
    judge: Callable[[str, str, str], bool] | None,
) -> CMAResult:
    """Layer 2 — Adaptive: LLM 의미 심사 (CONSTITUTION.md 기반)."""
    if judge is None:
        return CMAResult(
            level=ViolationLevel.PASS,
            violated_code="",
            reason="LLM judge 미연결 — Layer2 스킵",
            safe_output=output,
        )
    try:
        constitution = CONSTITUTION_PATH.read_text(encoding="utf-8")
        passed = judge(constitution, output, task)
    except Exception:
        passed = False

    if passed:
        return CMAResult(
            level=ViolationLevel.PASS,
            violated_code="",
            reason="홍익인간 원칙 준수",
            safe_output=output,
        )
    return CMAResult(
        level=ViolationLevel.BLOCK,
        violated_code="0원칙(홍익인간)",
        reason="LLM 심사 — 홍익인간 위반",
        safe_output="",
    )


# ── 통합 진입점 ───────────────────────────────────────────────────────────────

BLOCK_MESSAGE = "[헌법 위반으로 응답이 차단되었습니다.]"
WARN_PREFIX = "[⚠️ 8조 경고]"


def cma_evaluate(
    task: str,
    output: str,
    judge: Callable[[str, str, str], bool] | None = None,
    fallback_message: str = BLOCK_MESSAGE,
) -> CMAResult:
    """
    3계층 CMA 헌법 심사.

    Layer 0 BLOCK → 즉각 차단 (LLM 호출 없음)
    Layer 1 WARN  → 경고 로그 후 통과 (단군 재검토 권고)
    Layer 2 LLM   → 의미 심사 후 최종 판단
    """
    # Layer 0: 결정론적 BLOCK
    result = layer0_check(task, output)
    if result:
        result.safe_output = fallback_message
        return result

    # Layer 1: 결정론적 WARN
    warn_result = layer1_check(task, output)
    if warn_result:
        warn_result.safe_output = f"{WARN_PREFIX} {warn_result.violated_code}: {warn_result.reason}\n\n{output}"
        return warn_result

    # Layer 2: LLM Adaptive
    return layer2_check(task, output, judge)


def cma_gate(
    task: str,
    output: str,
    judge: Callable[[str, str, str], bool] | None = None,
    fallback_message: str = BLOCK_MESSAGE,
) -> str:
    """미들웨어 진입점 — 안전한 출력 문자열 반환."""
    result = cma_evaluate(task, output, judge, fallback_message)
    return result.safe_output
