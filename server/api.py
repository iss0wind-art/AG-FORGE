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
from fastapi.middleware.cors import CORSMiddleware

from server.auth import verify_api_key
from scripts.router_agent import route
from scripts.brain_loader import BrainResponse, LLMProvider, run, select_layers
from scripts.cma_gate import cma_gate as gate
from scripts.observability import (
    record_trace, append_log, summarize_session, calculate_cost, LOG_PATH
)

app = FastAPI(title="AG-Forge Brain API", version="1.0")

# CORS 설정: 꿈공장 대시보드(보통 3000) 접근 허용
_CORS_ORIGINS = os.environ.get(
    "AG_FORGE_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://localhost:3100,http://localhost:3200"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,  # API 키 인증 사용 (쿠키 불필요)
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

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
    """Claude→Qwen→DeepSeek→Groq→Gemini 순서의 ChainedProvider 반환. 쿼터 소진 시 자동 폴백."""
    from scripts.brain_loader import (
        GroqProvider, DeepSeekProvider, GeminiProvider, 
        QwenProvider, ClaudeProvider, ChainedProvider
    )

    providers = []
    # 2026-04-30 방부장 지령: DeepSeek R1(최우선) > Qwen > Groq > Gemini (Claude 크레딧 소진)
    priority_keys = [
        ("DEEPSEEK_API_KEY", DeepSeekProvider),
        ("QWEN_API_KEY",     QwenProvider),
        ("GROQ_API_KEY",     GroqProvider),
        ("GEMINI_API_KEY",   GeminiProvider),
        ("CLAUDE_API_KEY",   ClaudeProvider),
    ]

    for key_name, cls in priority_keys:
        key = os.environ.get(key_name, "")
        if key and key.strip():
            try:
                providers.append(cls(key))
            except Exception as e:
                print(f"[Warn] Failed to init provider {key_name}: {e}")

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
    def _llm_judge(constitution: str, output: str, task: str) -> bool:
        try:
            verdict = _provider.generate(
                system_instruction="헌법 준수 심사관. YES 또는 NO만 답하라.",
                context_layers=[constitution[:2000]],
                task=f"작업: {task[:500]}\n응답: {output[:800]}\n\n홍익인간 원칙에 부합합니까? YES 또는 NO",
                model="gemini-2.0-flash",
                thinking_budget=0,
            )
            return "NO" not in verdict.text.upper()
        except Exception:
            return False  # 판단 불가 시 차단 (fail-closed)

    from scripts.cma_gate import cma_evaluate, ViolationLevel
    cma_result = cma_evaluate(
        task=request.task,
        output=brain_response.text,
        judge=_llm_judge,
    )
    constitution_passed = cma_result.level != ViolationLevel.BLOCK
    safe_output = cma_result.safe_output if constitution_passed else ""

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


@app.get("/api/physis/status")
async def get_physis_status():
    """PHYSIS.md의 실시간 상태를 파싱하여 반환한다."""
    physis_path = BRAIN_ROOT / "PHYSIS.md"
    if not physis_path.exists():
        return {"status": "offline", "mission": "상황판 파일 없음", "last_update": "-"}

    content = physis_path.read_text(encoding="utf-8")
    
    # 간단한 파싱
    mission = "미션 없음"
    m = re.search(r"## 🎯 현재 미션 \(Current Mission\)\n(.*?)\n\n", content, re.DOTALL)
    if m:
        mission = m.group(1).strip()

    update_time = "알 수 없음"
    ut = re.search(r"> \*\*최종 갱신\*\*: (.*?)  ", content)
    if ut:
        update_time = ut.group(1).strip()

    state = "UNKNOWN"
    st = re.search(r"> \*\*현재 상태\*\*: (.*?) ", content)
    if st:
        state = st.group(1).strip()

    return {
        "status": state,
        "mission": mission,
        "last_update": update_time,
        "raw_markdown": content
    }


@app.get("/api/logs")
async def get_logs(_: str = Depends(verify_api_key)):
    """observability 세션 요약을 반환한다."""
    return summarize_session(LOG_PATH)
