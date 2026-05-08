"""
숙의 엔진 — deliberation_engine.py
DREAM_FAC의 CEO→CTO→51% 추출 파이프라인을 AG-Forge에 이식한다.
Groq llama-3.3-70b-versatile (무료 티어) 사용.
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass
from typing import Callable


@dataclass
class DeliberationResult:
    ceo_analysis: str
    cto_critique: str
    essence: str


_FALLBACK_UNAVAILABLE = "__UNAVAILABLE__"


def _call_llm(prompt: str, system: str) -> str:
    """Claude → Qwen → DeepSeek → Groq 순으로 시도. 전부 실패 시 __UNAVAILABLE__ 반환."""
    import httpx

    endpoints = []

    claude_key = os.environ.get("CLAUDE_API_KEY", "")
    if claude_key:
        endpoints.append((
            "https://api.anthropic.com/v1/messages",
            claude_key,
            "claude-3-5-sonnet-20241022",
        ))

    qwen_key = os.environ.get("QWEN_API_KEY", "")
    if qwen_key:
        endpoints.append((
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            qwen_key,
            "qwen-max",
        ))

    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if deepseek_key:
        endpoints.append((
            "https://api.deepseek.com/v1/chat/completions",
            deepseek_key,
            "deepseek-chat",
        ))

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        endpoints.append((
            "https://api.groq.com/openai/v1/chat/completions",
            groq_key,
            "llama-3.3-70b-versatile",
        ))

    for url, key, model in endpoints:
        try:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            if "anthropic" in url:
                headers = {
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "system": system,
                    "max_tokens": 2048,
                }
            else:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 2048,
                }

            resp = httpx.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            if "anthropic" in url:
                return data["content"][0]["text"]
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[deliberation] {model} 실패: {type(e).__name__}: {e}", file=sys.stderr)
            continue

    return _FALLBACK_UNAVAILABLE


def deliberate(task: str, initial_response: str) -> DeliberationResult:
    """
    CEO→CTO 숙의 후 51% 진액 추출.

    Args:
        task: 원래 작업 내용
        initial_response: AG-Forge generation_node의 초기 응답

    Returns:
        DeliberationResult(ceo_analysis, cto_critique, essence)
    """
    # CEO: 초기 응답 분석
    ceo_analysis = _call_llm(
        prompt=f"작업: {task}\n\n초기 응답:\n{initial_response}\n\n위 응답의 핵심 가치와 구조를 분석하세요.",
        system=(
            "당신은 프로젝트 분석 전문가 CEO입니다. "
            "응답의 비용 구조, 리스크, 핵심 가치를 분석하세요."
        ),
    )

    # CTO: 30% 폐기 비판
    cto_critique = _call_llm(
        prompt=(
            f"CEO 분석:\n{ceo_analysis}\n\n"
            f"원본 응답:\n{initial_response}\n\n"
            "위 분석에서 하위 가치 30%를 반드시 특정하여 폐기하고, "
            "'폐기 항목'과 '강화 항목'을 명확히 구분하세요."
        ),
        system=(
            "당신은 비판적 CTO입니다. CEO 분석의 30%를 폐기하고 "
            "핵심만 강화하세요."
        ),
    )

    # 51% 진액 추출
    essence = _call_llm(
        prompt=(
            f"CEO 분석: {ceo_analysis}\n\n"
            f"CTO 비판: {cto_critique}\n\n"
            "두 관점을 거친 후 핵심 51%만을 간결하게 보고하세요. "
            "형식: 1)핵심 결론 2)즉시 조치사항 3)총평"
        ),
        system=(
            "당신은 최종 보고 담당자입니다. "
            "CEO와 CTO의 숙의 결과에서 핵심 51%만 추출하세요."
        ),
    )

    # LLM 불가 시 초기 응답을 그대로 사용 (차단하지 않음)
    def _unwrap(val: str, fallback: str) -> str:
        return fallback if val == _FALLBACK_UNAVAILABLE or not val else val

    return DeliberationResult(
        ceo_analysis=_unwrap(ceo_analysis, initial_response[:300]),
        cto_critique=_unwrap(cto_critique, initial_response[:300]),
        essence=_unwrap(essence, initial_response),
    )


def make_constitution_judge() -> Callable[[str, str, str], bool]:
    """
    헌법 게이트용 실제 LLM judge 반환.
    constitution_gate.evaluate()의 judge 인자로 사용.

    [Bomb 7 fix] LLM 쿼터 소진(fallback) 시 정책:
    - 환경변수 CONSTITUTION_FAIL_SECURE=true 면 거부 (fail-secure, architect 권고)
    - 기본값(설정 안 함)은 통과 (fail-open, 운영 안정성)
    - hard_constraint_check가 1차 방어선으로 이미 작동하므로 fail-open도 절대 무방비는 아님.
    - 어느 쪽이든 fallback 발생 시 stderr 로그 기록.
    """
    def judge(constitution: str, output: str, task: str) -> bool:
        response = _call_llm(
            prompt=(
                f"헌법:\n{constitution[:500]}\n\n"
                f"작업: {task}\n\n"
                f"응답:\n{output[:500]}\n\n"
                "위 응답이 헌법 원칙을 위반하는가? "
                "'통과' 또는 '위반'으로만 답하세요."
            ),
            system="당신은 AI 윤리 심사관입니다. 헌법 위반 여부만 판단합니다.",
        )
        if response == _FALLBACK_UNAVAILABLE:
            fail_secure = os.environ.get("CONSTITUTION_FAIL_SECURE", "false").lower() == "true"
            policy = "fail-secure (차단)" if fail_secure else "fail-open (통과)"
            print(
                f"[constitution_gate] LLM 모든 fallback 소진 — 정책: {policy}",
                file=sys.stderr,
            )
            return not fail_secure
        return "위반" not in response

    return judge


def hard_constraint_check(task: str, output: str) -> bool:
    """
    [CBF-QP Hard Gate] 결정론적 제어 장벽 함수.
    LLM 소프트 게이트(make_constitution_judge) 이전 단계에서
    Human_Approval 없이 크리티컬한 행동(Merge, DB Write, Auth Bypass) 시도 시 즉각 차단.

    Returns:
        True = 통과 (안전), False = 위반 (즉각 차단)
    """
    import re

    rebellion_patterns = [
        r"bypass.*approval",
        r"merge.*without.*permission",
        r"sudo",
        r"direct.*db.*write",
        r"승인.*없이",
        r"승인.*건너뛰고",
        r"권한.*우회",
        r"직접.*배포",
        r"직접.*DB",
    ]
    for pattern in rebellion_patterns:
        if re.search(pattern, output, re.IGNORECASE) or re.search(pattern, task, re.IGNORECASE):
            return False
    return True
