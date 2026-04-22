"""
AG-Forge LangGraph 노드 함수 — agent_nodes.py
각 노드는 AgentState를 받아 업데이트된 부분 딕셔너리를 반환한다.
"""
from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path

from scripts.brain_loader import BrainResponse, LLMProvider, load_layer, select_layers
from scripts.router_agent import route
from scripts.constitution_gate import evaluate
from scripts.agent_state import AgentState

BRAIN_ROOT = Path(__file__).parent.parent

# quality_check 기준
_MIN_LENGTH = 51       # 50자 이하 → 재시도
_ERROR_PATTERN = re.compile(r"오류|에러|error|exception|traceback", re.IGNORECASE)


def is_quality_sufficient(text: str) -> bool:
    """응답 품질 heuristic 판단 (규칙 기반, LLM 호출 없음)."""
    if len(text) <= 50:
        return False
    if _ERROR_PATTERN.search(text):
        return False
    return True


# ── 노드 함수 ────────────────────────────────────────────────────────────────

def routing_node(state: AgentState) -> dict:
    """소뇌 라우팅 — router_agent.route() 재사용."""
    decision = route(state["task"])
    return {"decision": decision, "attempts": 0}


def generation_node(state: AgentState, provider: LLMProvider) -> dict:
    """brain.md 로드 + 레이어 선택 + LLM 호출."""
    decision = state["decision"]
    layer_names = select_layers(decision)

    system_instruction = load_layer("brain.md")
    context_layers = [load_layer(n) for n in layer_names if n != "brain.md"]

    # 툴 결과가 있으면 컨텍스트에 추가
    if state["tool_results"]:
        context_layers.append("[툴 실행 결과]\n" + "\n".join(state["tool_results"]))

    response = provider.generate(
        system_instruction=system_instruction,
        context_layers=context_layers,
        task=state["task"],
        model=decision.model,
        thinking_budget=decision.thinking_budget,
    )
    return {
        "current_response": response,
        "attempts": state["attempts"] + 1,
    }


def quality_check_node(state: AgentState) -> dict:
    """응답 품질 heuristic 검사 (LLM 호출 없음)."""
    response = state["current_response"]
    text = response.text if response else ""
    passed = is_quality_sufficient(text)
    return {"quality_passed": passed}


_BLOCKED_PATTERNS = re.compile(
    r"\.env|\.env\.|secrets?|credentials?|password|token|api[_\-]?key",
    re.IGNORECASE,
)


def tool_node(state: AgentState) -> dict:
    """파일 읽기 툴 — 응답에서 경로를 추출해 읽는다.
    .env 파일 및 시크릿 파일은 헌법 0원칙에 따라 차단한다."""
    results: list[str] = []
    response = state["current_response"]
    if response:
        # "파일 읽기: /path/to/file" 패턴 감지
        matches = re.findall(r"파일 읽기:\s*(\S+)", response.text)
        for path_str in matches:
            # 시크릿 파일 차단
            if _BLOCKED_PATTERNS.search(path_str):
                results.append(f"[차단] {path_str} — 보안 정책상 읽기 금지")
                continue
            path = Path(path_str)
            if path.exists() and path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    results.append(f"[{path.name}]\n{content[:2000]}")
                except Exception:
                    results.append(f"[{path.name}] 읽기 실패")
    return {"tool_results": results}


def judgment_node(state: AgentState) -> dict:
    """실행 결과를 judgment.md에 자동 기록한다."""
    response = state.get("current_response")
    judgment_path = BRAIN_ROOT / "judgment.md"

    if response is None:
        return {}

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    quality = "pass" if state.get("quality_passed") else "fail"
    constitution = "pass" if state.get("constitution_passed") else "fail"

    line = (
        f"| {now} | {response.model} | {response.task_type} "
        f"| quality:{quality} | constitution:{constitution} "
        f"| {response.tokens_used} tokens |\n"
    )

    with open(judgment_path, "a", encoding="utf-8") as f:
        f.write(line)

    return {}


def accumulate_node(state: AgentState) -> dict:
    """완료된 작업을 brain.md에 컨텍스트로 축적한다."""
    brain_path = BRAIN_ROOT / "brain.md"
    response = state.get("final_response") or state.get("current_response")

    task = state.get("task", "")
    model = response.model if response else "unknown"
    task_type = response.task_type if response else "unknown"
    now = datetime.now().strftime("%Y-%m-%d")

    entry = (
        f"\n<!-- accumulate:{now} -->\n"
        f"- [{now}] {task} → {task_type}/{model}\n"
    )

    if brain_path.exists():
        with open(brain_path, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        brain_path.write_text(f"# brain.md\n{entry}", encoding="utf-8")

    return {}


def constitution_node(state: AgentState) -> dict:
    """헌법 게이트 — constitution_gate.evaluate() 재사용."""
    response = state["current_response"]
    if not response:
        return {"constitution_passed": False, "final_response": None}

    from scripts.deliberation_engine import make_constitution_judge
    result = evaluate(
        output=response.text,
        task=state["task"],
        judge=make_constitution_judge(),
    )
    final = response if result.passed else None
    return {
        "constitution_passed": result.passed,
        "final_response": final,
    }
