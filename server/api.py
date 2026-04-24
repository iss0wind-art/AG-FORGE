"""
AG-Forge API 서버 — api.py
모바일에서 뇌에 명령을 내리고 응답을 받는다.
"""
from __future__ import annotations
import asyncio
import os
import re
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
from pathlib import Path

from server.auth import verify_api_key
from scripts.router_agent import route
from scripts.brain_loader import BrainResponse, LLMProvider, run, select_layers
from scripts.constitution_gate import gate
from scripts.observability import (
    record_trace, append_log, summarize_session, calculate_cost, LOG_PATH
)

app = FastAPI(title="AG-Forge Brain API", version="1.0")

BRAIN_ROOT = Path(__file__).parent.parent
UI_PATH = Path(__file__).parent / "static" / "index.html"


# ── 내부 FakeProvider (실제 Gemini 키 없을 때 fallback) ──────────────────
class _InternalProvider(LLMProvider):
    """Gemini API 키가 없을 때 사용하는 내부 fallback 프로바이더."""

    def generate(self, system_instruction, context_layers, task, model, thinking_budget):
        routing = route(task)
        return BrainResponse(
            text=f"[{model}] {task} → 라우팅 완료. 실제 응답은 Gemini API 키 설정 후 활성화됩니다.",
            model=model,
            task_type=routing.task_type.value,
            tokens_used=300,
            cache_hit=False,
        )


def _build_provider() -> LLMProvider:
    """Claude→Qwen→DeepSeek→Gemini→Groq 순서의 ChainedProvider 반환. 쿼터 소진 시 자동 폴백."""
    from scripts.brain_loader import (
        ClaudeProvider, QwenProvider, DeepSeekProvider, GeminiProvider, GroqProvider, ChainedProvider
    )

    providers = []
    for key_name, cls in [
        ("CLAUDE_API_KEY",   ClaudeProvider),
        ("QWEN_API_KEY",    QwenProvider),
        ("DEEPSEEK_API_KEY", DeepSeekProvider),
        ("GEMINI_API_KEY",   GeminiProvider),
        ("GROQ_API_KEY",    GroqProvider),
    ]:
        key = os.environ.get(key_name, "")
        if key:
            try:
                providers.append(cls(key))
            except Exception:
                pass

    if providers:
        return ChainedProvider(providers)
    return _InternalProvider()

_provider = _build_provider()


# ── 스키마 ────────────────────────────────────────────────────────────────

class TaskRequest(BaseModel):
    task: str

    @field_validator("task")
    @classmethod
    def task_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("task는 비어있을 수 없습니다.")
        return v.strip()


# ── 라우트 ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def mobile_ui():
    """모바일 웹 UI."""
    if os.environ.get("AG_FORGE_HEADLESS") == "true":
        return HTMLResponse(
            content="<html><body><h1>AG-Forge Headless Mode</h1><p>UI is disabled. Use API endpoints.</p></body></html>",
            status_code=403,
            media_type="text/html; charset=utf-8"
        )
    
    try:
        # utf-8-sig를 사용하여 Windows BOM 문제 해결
        ui_content = UI_PATH.read_text(encoding="utf-8-sig")
    except Exception:
        try:
            ui_content = UI_PATH.read_text(encoding="utf-8")
        except Exception:
            ui_content = UI_PATH.read_text(encoding="cp949", errors="replace")
            
    return HTMLResponse(content=ui_content, media_type="text/html; charset=utf-8")


@app.post("/api/task")
async def submit_task(
    request: TaskRequest,
    _: str = Depends(verify_api_key),
):
    """뇌에 작업을 전송하고 응답을 반환한다."""
    decision = route(request.task)
    layers = select_layers(decision)

    brain_response = await asyncio.to_thread(run, request.task, _provider)

    # 헌법 게이트 통과 여부
    safe_output = gate(
        brain_response.text,
        request.task,
        judge=lambda constitution, output, task: True,  # TODO: 실제 LLM judge 연결
    )
    constitution_passed = safe_output == brain_response.text

    # 비용 계산 및 로그
    cost = calculate_cost(
        brain_response.model if brain_response.model in ("gemini-2.5-pro", "gemini-2.0-flash")
        else "gemini-2.5-pro",
        int(brain_response.tokens_used * 0.7),
        int(brain_response.tokens_used * 0.3),
    )
    record = record_trace(brain_response, request.task, layers)
    append_log(record)

    # 응답 사전에 한글 깨짐 방지를 위한 조치 포함 가능
    return {
        "response": safe_output,
        "model": brain_response.model,
        "task_type": brain_response.task_type,
        "tokens_used": brain_response.tokens_used,
        "cache_hit": brain_response.cache_hit,
        "cost_usd": cost,
        "constitution_passed": constitution_passed,
        "layers_loaded": layers,
    }


@app.get("/api/status")
async def get_status(_: str = Depends(verify_api_key)):
    """현재 brain.md 상태를 반환한다."""
    brain_path = BRAIN_ROOT / "brain.md"
    try:
        content = brain_path.read_text(encoding="utf-8-sig")
    except Exception:
        try:
            content = brain_path.read_text(encoding="utf-8")
        except Exception:
            content = brain_path.read_text(encoding="cp949", errors="replace")

    # 현재 작업 상태 섹션 추출
    summary_match = re.search(r"## 8\..*?```yaml(.*?)```", content, re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else content[:300]

    # judgment.md에서 마지막 라우팅 로그 추출
    judgment_path = BRAIN_ROOT / "judgment.md"
    try:
        judgment = judgment_path.read_text(encoding="utf-8-sig")
    except Exception:
        judgment = judgment_path.read_text(encoding="utf-8", errors="replace")

    log_lines = [l for l in judgment.splitlines() if "|" in l and "gemini" in l.lower()]
    last_routing = log_lines[-1].strip() if log_lines else "없음"

    return {
        "brain_summary": summary,
        "active_layer": "brain.md",
        "last_routing": last_routing,
    }


@app.get("/api/logs")
async def get_logs(_: str = Depends(verify_api_key)):
    """observability 세션 요약을 반환한다."""
    return summarize_session(LOG_PATH)
