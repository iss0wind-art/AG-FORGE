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
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore  # 테스트 환경에서 SDK 없어도 동작

from scripts.router_agent import RoutingDecision, TaskType, route

BRAIN_ROOT = Path(__file__).parent.parent

_LAYER_FILES = {
    TaskType.UI:           ["PHYSIS_CHARTER.md", "brain.md", "emotion_ui.md"],
    TaskType.PLANNING:     ["PHYSIS_CHARTER.md", "brain.md"],
    TaskType.CODE:         ["PHYSIS_CHARTER.md", "brain.md", "logic_rb.md"],
    TaskType.ARCHITECTURE: ["PHYSIS_CHARTER.md", "brain.md", "logic_rb.md", "emotion_ui.md"],
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


class GroqProvider(LLMProvider):
    """Groq OpenAI-호환 API 기반 구현. 무료 티어 llama-3.3-70b-versatile."""

    _BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Groq API 키가 필요합니다.")
        self._api_key = api_key

    def generate(
        self,
        system_instruction: str,
        context_layers: list[str],
        task: str,
        model: str,
        thinking_budget: int,
    ) -> BrainResponse:
        import httpx

        full_context = "\n\n---\n\n".join(context_layers)

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": f"{system_instruction}\n\n{full_context}"},
                {"role": "user", "content": task},
            ],
            "max_tokens": 8192,
        }

        resp = httpx.post(
            self._BASE_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)

        return BrainResponse(
            text=text,
            model="llama-3.3-70b-versatile",
            task_type="groq",
            tokens_used=tokens,
            cache_hit=False,
        )


class DeepSeekProvider(LLMProvider):
    """DeepSeek OpenAI-호환 API 기반 구현. httpx 사용."""

    _BASE_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("DeepSeek API 키가 필요합니다.")
        self._api_key = api_key

    def generate(
        self,
        system_instruction: str,
        context_layers: list[str],
        task: str,
        model: str,
        thinking_budget: int,
    ) -> BrainResponse:
        import httpx

        full_context = "\n\n---\n\n".join(context_layers)
        # thinking_budget이 클수록 복잡한 작업 → deepseek-reasoner (R1)
        ds_model = "deepseek-reasoner" if thinking_budget >= 8000 else "deepseek-chat"

        payload = {
            "model": ds_model,
            "messages": [
                {"role": "system", "content": f"{system_instruction}\n\n{full_context}"},
                {"role": "user", "content": task},
            ],
            "max_tokens": 8192,
        }

        resp = httpx.post(
            self._BASE_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)

        return BrainResponse(
            text=text,
            model=ds_model,
            task_type="deepseek",
            tokens_used=tokens,
            cache_hit=False,
        )


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API 기반 구현. anthropic SDK + ephemeral prompt caching 사용."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Claude API 키가 필요합니다.")
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(
        self,
        system_instruction: str,
        context_layers: list[str],
        task: str,
        model: str,
        thinking_budget: int,
    ) -> BrainResponse:
        full_context = "\n\n---\n\n".join(context_layers)
        claude_model = "claude-sonnet-4-6"

        response = self.client.messages.create(
            model=claude_model,
            max_tokens=4096,
            system=[
                {"type": "text", "text": system_instruction},
                {"type": "text", "text": full_context, "cache_control": {"type": "ephemeral"}},
            ],
            messages=[{"role": "user", "content": task}],
        )

        return BrainResponse(
            text=response.content[0].text,
            model=claude_model,
            task_type="claude",
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            cache_hit=getattr(response.usage, "cache_read_input_tokens", 0) > 0,
        )


class QwenProvider(LLMProvider):
    """DashScope(Qwen) 3.6 Plus Thinking 모델 기반 구현. 국제판 엔드포인트 사용."""

    _BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Qwen API 키가 필요합니다.")
        self._api_key = api_key

    def generate(
        self,
        system_instruction: str,
        context_layers: list[str],
        task: str,
        model: str,
        thinking_budget: int,
    ) -> BrainResponse:
        import httpx

        full_context = "\n\n---\n\n".join(context_layers)
        q_model = "qwen3.6-plus"

        payload = {
            "model": q_model,
            "messages": [
                {"role": "system", "content": f"{system_instruction}\n\n{full_context}"},
                {"role": "user", "content": task},
            ],
            "enable_thinking": True,
        }

        resp = httpx.post(
            self._BASE_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()

        message = data["choices"][0]["message"]
        content = message.get("content", "")
        reasoning = message.get("reasoning_content", "")

        final_text = content
        if reasoning:
            final_text = f"--- [Thinking Process] ---\n{reasoning}\n\n--- [Final Response] ---\n{content}"

        return BrainResponse(
            text=final_text,
            model=q_model,
            task_type="qwen",
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
            cache_hit=False,
        )


def load_layer(layer_name: str) -> str:
    """뇌 계층 파일을 로드한다."""
    path = Path(__file__).parent.parent / layer_name
    if not path.exists():
        return ""
    try:
        # utf-8-sig를 우선적으로 사용하여 BOM 처리
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="cp949")
            except Exception:
                return path.read_text(encoding="utf-8", errors="replace")


def select_layers(decision: RoutingDecision) -> list[str]:
    """RoutingDecision에 따라 로드할 레이어 목록을 결정한다. brain.md는 항상 첫 번째."""
    return list(_LAYER_FILES[decision.task_type])


class ChainedProvider(LLMProvider):
    """429/쿼터 소진 시 다음 프로바이더로 자동 전환하는 체인 래퍼."""

    def __init__(self, providers: list[LLMProvider]) -> None:
        if not providers:
            raise ValueError("프로바이더 목록이 비어있습니다.")
        self._providers = providers

    def generate(
        self,
        system_instruction: str,
        context_layers: list[str],
        task: str,
        model: str,
        thinking_budget: int,
    ) -> BrainResponse:
        last_exc: Exception | None = None
        for provider in self._providers:
            try:
                return provider.generate(
                    system_instruction, context_layers, task, model, thinking_budget
                )
            except Exception as e:
                error_str = str(e).lower()
                response_text = ""
                if hasattr(e, "response") and hasattr(e.response, "text"):
                    response_text = e.response.text.lower()
                
                if ("429" in error_str or "quota" in error_str or "rate" in error_str or
                    "credit" in response_text or "balance" in response_text or "400" in error_str):
                    last_exc = e
                    continue
                raise
        raise last_exc or RuntimeError("모든 프로바이더 쿼터 소진")


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
