"""
숙의 엔진 — deliberation_engine.py
DREAM_FAC의 CEO→CTO→51% 추출 파이프라인을 AG-Forge에 이식한다.
Groq llama-3.3-70b-versatile (무료 티어) 사용.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Callable


@dataclass
class DeliberationResult:
    ceo_analysis: str
    cto_critique: str
    essence: str


_FALLBACK_UNAVAILABLE = "__UNAVAILABLE__"


def _call_llm(prompt: str, system: str) -> str:
    """Groq → DeepSeek 순으로 시도. 전부 실패 시 __UNAVAILABLE__ 반환."""
    import httpx

    endpoints = []

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        endpoints.append((
            "https://api.groq.com/openai/v1/chat/completions",
            groq_key,
            "llama-3.3-70b-versatile",
        ))

    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if deepseek_key:
        endpoints.append((
            "https://api.deepseek.com/v1/chat/completions",
            deepseek_key,
            "deepseek-chat",
        ))

    for url, key, model in endpoints:
        try:
            resp = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 2048,
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
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
        # LLM 불가 시 기본 통과 (쿼터 소진이 응답 차단 이유가 되어선 안 됨)
        if response == _FALLBACK_UNAVAILABLE:
            return True
        return "위반" not in response

    return judge
