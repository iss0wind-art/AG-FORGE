"""
피지수(Piji-soo) MCP 서버 — mcp_server.py
Claude Code에서 피지수 독립 뇌를 직접 호출한다.
stdio 전송 방식 (Claude Code 표준).

Claude Code settings.json 등록:
{
  "mcpServers": {
    "piji-soo": {
      "command": "python",
      "args": ["d:/Git/AG-Forge/mcp_server.py"]
    }
  }
}

호출 방식:
  Claude Code 채팅에서 자연스럽게 "피지수야 ..." 라고 호출하면 자동 응답
  또는 @piji-soo 명령어로 명시적 호출도 가능
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

mcp = FastMCP("piji-soo")

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
def piji_soo(task: str) -> str:
    """
    피지수 독립 뇌에 작업을 전달하고 응답을 반환한다.
    헌법 게이트(CONSTITUTION.md)를 통과한 응답만 반환된다.

    Claude Code에서 "피지수야" 라고 호출하면 자동으로 이 도구가 실행됨.
    예: "피지수야 이 함수 최적화해줄 수 있어?"

    Args:
        task: 수행할 작업 또는 질문 (예: "이 코드 리뷰해줘", "아키텍처 설계해줘")

    Returns:
        헌법 게이트를 통과한 피지수의 응답 텍스트
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
def piji_soo_status() -> dict:
    """
    피지수의 현재 상태를 반환한다.
    brain.md 요약과 마지막 라우팅 정보를 포함한다.
    
    반환:
        피지수 상태 정보 (뇌 활성화 상황, 마지막 작업 로그)
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
def piji_soo_logs() -> dict:
    """
    피지수의 observability 세션 통계를 반환한다.
    총 요청 수, 누적 비용, 캐시 히트율 등.

    Returns:
        피지수 활동 리포트 (비용/캐시/성능)
    """
    return summarize_session(LOG_PATH)


# ── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
