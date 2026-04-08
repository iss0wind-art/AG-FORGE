"""
전두엽 로더 — brain_loader.py
brain.md + 레이어 파일을 Gemini CachedContent API로 로드한다.
LLMProvider 추상화로 추후 Claude 이식 가능.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore  # 테스트 환경에서 SDK 없어도 동작

from scripts.router_agent import RoutingDecision, TaskType, route

BRAIN_ROOT = Path(__file__).parent.parent

_LAYER_FILES = {
    TaskType.UI:           ["brain.md", "emotion_ui.md"],
    TaskType.PLANNING:     ["brain.md"],
    TaskType.CODE:         ["brain.md", "logic_rb.md"],
    TaskType.ARCHITECTURE: ["brain.md", "logic_rb.md", "emotion_ui.md"],
}


@dataclass
class BrainResponse:
    text: str
    model: str
    task_type: str
    tokens_used: int
    cache_hit: bool


class LLMProvider(ABC):
    """Gemini / Claude 교체 가능한 추상 레이어."""

    @abstractmethod
    def generate(
        self,
        system_instruction: str,
        context_layers: list[str],
        task: str,
        model: str,
        thinking_budget: int,
    ) -> BrainResponse:
        ...


class GeminiProvider(LLMProvider):
    """Google Gemini CachedContent 기반 구현."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Gemini API 키가 필요합니다.")
        if genai is None:
            raise ImportError("google-generativeai 패키지를 설치하세요: pip install google-generativeai")
        genai.configure(api_key=api_key)
        self._api_key = api_key

    def generate(
        self,
        system_instruction: str,
        context_layers: list[str],
        task: str,
        model: str,
        thinking_budget: int,
    ) -> BrainResponse:
        """
        Gemini API 호출.
        컨텍스트가 32k tokens 이상이면 CachedContent를 사용하고,
        미만이면 직접 호출한다.
        """
        import datetime

        full_context = "\n\n---\n\n".join(context_layers)
        combined_size = len(system_instruction) + len(full_context)

        # 32k tokens ≈ 128,000 chars (UTF-8 평균 4bytes/token 기준)
        use_cache = combined_size > 128_000

        # 무료 티어에서 2.5-pro 할당량 초과 시 flash로 자동 강등
        _FALLBACK_MODEL = "gemini-2.0-flash"

        def _call_model(m: str) -> object:
            if use_cache:
                cache = genai.caching.CachedContent.create(
                    model=f"models/{m}",
                    system_instruction=system_instruction,
                    contents=[full_context],
                    ttl=datetime.timedelta(minutes=5),
                )
                gm = genai.GenerativeModel.from_cached_content(cache)
                r = gm.generate_content(task)
                cache.delete()
                return r
            else:
                gm = genai.GenerativeModel(
                    model_name=m,
                    system_instruction=system_instruction,
                )
                return gm.generate_content(f"{full_context}\n\n---\n\n{task}")

        try:
            response = _call_model(model)
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(type(e).__name__):
                model = _FALLBACK_MODEL
                response = _call_model(model)
            else:
                raise

        return BrainResponse(
            text=response.text,
            model=model,
            task_type="gemini",
            tokens_used=response.usage_metadata.total_token_count,
            cache_hit=use_cache,
        )


def load_layer(name: str) -> str:
    """뇌 레이어 파일을 읽어 반환한다."""
    path = BRAIN_ROOT / name
    if not path.exists():
        raise FileNotFoundError(f"레이어 파일을 찾을 수 없습니다: {path}")
    return path.read_text(encoding="utf-8")


def select_layers(decision: RoutingDecision) -> list[str]:
    """RoutingDecision에 따라 로드할 레이어 목록을 결정한다. brain.md는 항상 첫 번째."""
    return list(_LAYER_FILES[decision.task_type])


def run(task: str, provider: LLMProvider) -> BrainResponse:
    """
    LangGraph 자율 에이전트 루프 실행.
    외부 호출 인터페이스(run(task, provider) -> BrainResponse)는 유지된다.
    """
    from scripts.agent_graph import build_agent_graph
    from scripts.agent_state import AgentState

    graph = build_agent_graph(provider)

    initial_state: AgentState = {
        "task": task,
        "decision": None,
        "current_response": None,
        "attempts": 0,
        "quality_passed": False,
        "constitution_passed": False,
        "final_response": None,
        "error": None,
        "tool_results": [],
    }

    final_state = graph.invoke(initial_state)

    # 최종 응답 추출 — abort 경로에서도 마지막 응답 반환
    result = final_state.get("final_response") or final_state.get("current_response")
    if result is None:
        return BrainResponse(
            text="[에이전트 루프 실패: 응답을 생성할 수 없습니다.]",
            model="none",
            task_type=task,
            tokens_used=0,
            cache_hit=False,
        )
    return result
