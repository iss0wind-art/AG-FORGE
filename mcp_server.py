"""
피지수(Physis) MCP 서버 — mcp_server.py
Claude Code에서 피지수 독립 뇌를 직접 호출한다.
stdio 전송 방식 (Claude Code 표준).

Claude Code settings.json 등록:
{
  "mcpServers": {
    "physis": {
      "command": "python",
      "args": ["d:/Git/AG-Forge/mcp_server.py"]
    }
  }
}

호출 방식:
  Claude Code 채팅에서 자연스럽게 "피지수야 ..." 라고 호출하면 자동 응답
  또는 @physis 명령어로 명시적 호출도 가능
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

# EXCEL_DIAT 루트 추가 (합체 엔진)
_DIAT_ROOT = Path("D:/Git/EXCEL_DIAT")
if _DIAT_ROOT.exists():
    sys.path.insert(0, str(_DIAT_ROOT))

from scripts.brain_loader import BrainResponse, LLMProvider, run
from scripts.router_agent import route
from scripts.observability import summarize_session, LOG_PATH

mcp = FastMCP("physis")

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
    """Claude→Qwen→DeepSeek→Groq→Gemini 순서의 ChainedProvider 반환."""
    from scripts.brain_loader import (
        GroqProvider, DeepSeekProvider, GeminiProvider,
        QwenProvider, ClaudeProvider, ChainedProvider
    )

    providers = []
    # 방부장 지령 최신 서열 적용
    priority_keys = [
        ("CLAUDE_API_KEY",   ClaudeProvider),
        ("QWEN_API_KEY",     QwenProvider),
        ("DEEPSEEK_API_KEY", DeepSeekProvider),
        ("GEMINI_API_KEY",    GeminiProvider),
        ("GROQ_API_KEY",      GroqProvider),
    ]

    for key_name, cls in priority_keys:
        key = os.environ.get(key_name, "")
        if key and key.strip():
            try:
                providers.append(cls(key))
            except Exception as e:
                print(f"[physis] {key_name} 초기화 실패: {e}", file=sys.stderr)

    if providers:
        return ChainedProvider(providers)
    return _FallbackProvider()


# ── 툴 1: ask_brain ───────────────────────────────────────────────────────────

@mcp.tool()
def physis(task: str) -> str:
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
        print(f"[physis] run 실패: {type(exc).__name__}: {exc}", file=sys.stderr)
        return "[AG-Forge 오류] 뇌 응답 중 문제가 발생했습니다. 로그를 확인하세요."


# ── 툴 2: get_brain_status ────────────────────────────────────────────────────

@mcp.tool()
def physis_status() -> dict:
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
def physis_logs() -> dict:
    """
    피지수의 observability 세션 통계를 반환한다.
    총 요청 수, 누적 비용, 캐시 히트율 등.

    Returns:
        피지수 활동 리포트 (비용/캐시/성능)
    """
    return summarize_session(LOG_PATH)


# ── 툴 4: Excel Surgeon (EXCEL_DIAT 통합) ───────────────────────────────────

@mcp.tool()
def excel_surgical_diet(input_path: str, output_path: str = None) -> str:
    """
    대용량 엑셀 파일을 다이어트시킨다 (90% 이상 압축).
    노란색 셀(편집 대상)만 남기고 나머지 서식/이미지 등을 최적화한다.

    Args:
        input_path: 원본 엑셀 파일 경로 (예: "D:/Git/EXCEL_DIAT/large.xlsx")
        output_path: 결과 저장 경로 (기본값: input_path_diet.xlsx)

    Returns:
        수행 결과 메시지 및 생성된 파일 경로
    """
    try:
        from diet_engine import surgical_diet
        
        in_p = Path(input_path)
        if not in_p.exists():
            return f"[오류] 파일을 찾을 수 없습니다: {input_path}"
        
        if not output_path:
            output_path = str(in_p.parent / f"{in_p.stem}_diet{in_p.suffix}")
            
        success, msg = surgical_diet(input_path, output_path)
        if success:
            return f"[성공] 엑셀 수술 완료. 결과: {output_path} ({msg})"
        else:
            return f"[실패] {msg}"
    except Exception as e:
        return f"[엔진 오류] {str(e)}"


@mcp.tool()
def extract_boq_data(project_id: str) -> dict:
    """
    프로젝트 ID를 기준으로 다이어트된 엑셀에서 BOQ 내역 데이터를 추출한다.
    
    Args:
        project_id: EXCEL_DIAT 프로젝트 ID
        
    Returns:
        추출된 데이터 요약 (시트 목록, 항목 수 등)
    """
    # EXCEL_DIAT의 API 로직을 참고하여 구현 (현재는 메타데이터 반환 위주)
    try:
        project_dir = Path(f"D:/Git/EXCEL_DIAT/api/projects/{project_id}")
        diet_path = project_dir / "diet.xlsx"
        if not diet_path.exists():
            return {"status": "error", "message": f"프로젝트를 찾을 수 없습니다: {project_id}"}
            
        from openpyxl import load_workbook
        wb = load_workbook(str(diet_path), read_only=True, data_only=True)
        sheets = wb.sheetnames
        wb.close()
        
        return {
            "status": "success",
            "project_id": project_id,
            "sheets": sheets,
            "file_size": diet_path.stat().st_size
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def generate_gabji_report(project_id: str) -> dict:
    """
    공종별 집계표(갑지) 데이터를 생성한다.
    
    Args:
        project_id: EXCEL_DIAT 프로젝트 ID
        
    Returns:
        집계표 데이터 (전회, 금회, 누적 기성 등)
    """
    try:
        from gabji_engine import build_jibgye_table
        db_path = "D:/Git/EXCEL_DIAT/boq.db"
        
        rows = build_jibgye_table(db_path, project_id)
        if not rows:
            return {"status": "error", "message": "집계할 데이터가 없습니다."}
            
        return {
            "status": "success",
            "project_id": project_id,
            "jibgye": rows
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
