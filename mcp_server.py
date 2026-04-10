"""
AG-Forge MCP 서버 — mcp_server.py
Claude Code에서 AG-Forge 뇌를 직접 MCP 툴로 호출한다.
stdio 전송 방식 (Claude Code 표준).

Claude Code settings.json 등록:
{
  "mcpServers": {
    "ag-forge": {
      "command": "python",
      "args": ["d:/Git/AG-Forge/mcp_server.py"]
    }
  }
}
"""
from __future__ import annotations
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP

# AG-Forge 루트를 sys.path에 추가 (어떤 cwd에서 실행해도 동작)
_FORGE_ROOT = Path(__file__).parent
sys.path.insert(0, str(_FORGE_ROOT))

from scripts.brain_loader import BrainResponse, LLMProvider, run
from scripts.router_agent import route
from scripts.observability import summarize_session, LOG_PATH

mcp = FastMCP("ag-forge")

BRAIN_ROOT = _FORGE_ROOT


# ── Provider 빌드 ─────────────────────────────────────────────────────────────

class _FallbackProvider(LLMProvider):
    """Gemini API 키 없을 때 사용하는 MCP 전용 fallback."""

    def generate(self, system_instruction, context_layers, task, model, thinking_budget):
        routing = route(task)
        return BrainResponse(
            text=(
                f"[{model}] {task} → 라우팅 완료.\n"
                "실제 응답은 GEMINI_API_KEY 설정 후 활성화됩니다."
            ),
            model=model,
            task_type=routing.task_type.value,
            tokens_used=0,
            cache_hit=False,
        )


def _build_provider() -> LLMProvider:
    """Groq→DeepSeek→Gemini 순서의 ChainedProvider 반환. 쿼터 소진 시 자동 폴백."""
    from scripts.brain_loader import GroqProvider, DeepSeekProvider, GeminiProvider, ChainedProvider

    providers = []
    for key_name, cls in [
        ("DEEPSEEK_API_KEY", DeepSeekProvider),
        ("GROQ_API_KEY",    GroqProvider),
        ("GEMINI_API_KEY",   GeminiProvider),
    ]:
        key = os.environ.get(key_name, "")
        if key:
            try:
                providers.append(cls(key))
            except Exception:
                pass

    if providers:
        return ChainedProvider(providers)
    return _FallbackProvider()


# ── 툴 1: ask_brain ───────────────────────────────────────────────────────────

@mcp.tool()
def ask_brain(task: str) -> str:
    """
    AG-Forge 뇌(LangGraph 루프)에 작업을 전달하고 응답을 반환한다.
    헌법 게이트(CONSTITUTION.md)를 통과한 응답만 반환된다.

    Args:
        task: 수행할 작업 또는 질문 (예: "이 코드 리뷰해줘", "아키텍처 설계해줘")

    Returns:
        헌법 게이트를 통과한 뇌의 응답 텍스트
    """
    if not task.strip():
        return "[오류] task는 비어있을 수 없습니다."

    provider = _build_provider()

    try:
        result: BrainResponse = run(task.strip(), provider)
        return result.text
    except Exception as exc:
        return f"[AG-Forge 오류] {exc}"


# ── 툴 2: get_brain_status ────────────────────────────────────────────────────

@mcp.tool()
def get_brain_status() -> dict:
    """
    AG-Forge 뇌의 현재 상태를 반환한다.
    brain.md 요약과 마지막 라우팅 정보를 포함한다.

    Returns:
        brain_summary: brain.md 현재 작업 상태 요약
        active_layer: 현재 활성 레이어
        last_routing: judgment.md 마지막 라우팅 로그
    """
    brain_path = BRAIN_ROOT / "brain.md"
    judgment_path = BRAIN_ROOT / "judgment.md"

    try:
        content = brain_path.read_text(encoding="utf-8")
        summary_match = re.search(r"## 8\..*?```yaml(.*?)```", content, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else content[:300]
    except FileNotFoundError:
        summary = "[brain.md 없음]"

    try:
        judgment = judgment_path.read_text(encoding="utf-8")
        log_lines = [l for l in judgment.splitlines() if "|" in l and "gemini" in l.lower()]
        last_routing = log_lines[-1].strip() if log_lines else "없음"
    except FileNotFoundError:
        last_routing = "[judgment.md 없음]"

    return {
        "brain_summary": summary,
        "active_layer": "brain.md",
        "last_routing": last_routing,
    }


# ── 툴 3: get_brain_logs ──────────────────────────────────────────────────────

@mcp.tool()
def get_brain_logs() -> dict:
    """
    AG-Forge observability 세션 통계를 반환한다.

    Returns:
        total_requests: 총 요청 수
        total_cost_usd: 누적 비용 (USD)
        cache_hit_rate: 캐시 히트율 (0.0 ~ 1.0)
    """
    return summarize_session(LOG_PATH)


# ── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
