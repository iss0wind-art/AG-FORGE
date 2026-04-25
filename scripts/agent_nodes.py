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
    """파일 읽기/쓰기 및 명령어 실행 툴.
    파일 쓰기 및 명령어 실행은 사용자의 명시적 승인이 있어야 실제 수행된다."""
    results: list[str] = []
    response = state["current_response"]
    if not response:
        return {}

    # 1. 시각적 도구 정의 파싱
    read_matches = re.findall(r"파일 읽기:\s*(\S+)", response.text)
    write_matches = re.findall(r"파일 쓰기:\s*(\S+)\s*\n내용:\s*(.*?)(?=\n\n|\n툴|\Z)", response.text, re.DOTALL)
    run_matches = re.findall(r"명령어 실행:\s*(.*?)(?=\n\n|\n툴|\Z)", response.text)

    # 2. 읽기 도구 (자율 실행 가능)
    for path_str in read_matches:
        if _BLOCKED_PATTERNS.search(path_str):
            results.append(f"[차단] {path_str} — 보안 정책상 읽기 금지")
            continue
        path = Path(path_str)
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                results.append(f"[읽기 결과: {path.name}]\n{content[:2000]}")
            except Exception as e:
                results.append(f"[읽기 실패: {path.name}] {e}")

    # 3. 쓰기 및 실행 도구 (방부장 승인 필수)
    needs_approval = False
    pending_action = None

    # 쓰기 시도 감지
    if write_matches:
        target_path, content = write_matches[0]
        if _BLOCKED_PATTERNS.search(target_path):
            results.append(f"[차단] {target_path} — 보안 정책상 쓰기 금지")
        elif state.get("approved"):
            try:
                Path(target_path).write_text(content, encoding="utf-8")
                results.append(f"[쓰기 성공: {target_path}]")
            except Exception as e:
                results.append(f"[쓰기 실패: {target_path}] {e}")
        else:
            needs_approval = True
            pending_action = f"파일 쓰기: {target_path} (내용: {len(content)}자)"

    # 명령어 실행 시도 감지
    if run_matches:
        cmd = run_matches[0]
        if state.get("approved"):
            import subprocess
            try:
                out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True, timeout=30)
                results.append(f"[실행 결과: {cmd}]\n{out[:2000]}")
            except Exception as e:
                results.append(f"[실행 실패: {cmd}] {e}")
        else:
            needs_approval = True
            pending_action = f"명령어 실행: {cmd}"

    return {
        "tool_results": results,
        "needs_approval": needs_approval,
        "pending_tool_call": pending_action,
        "approved": False if needs_approval else state.get("approved", False)
    }


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
    """헌법 2단 게이트 — 1단(Hard, 결정론) → 2단(Soft, LLM judge).

    Bomb 2 fix: hard_constraint_check를 LLM 호출 전에 실행하여
    명백한 반란/우회 패턴은 결정론적으로 즉시 차단한다.
    """
    response = state["current_response"]
    if not response:
        return {"constitution_passed": False, "final_response": None}

    from scripts.deliberation_engine import make_constitution_judge, hard_constraint_check

    # 1단: Hard gate — 결정론적 정규식, LLM 호출 전 즉시 차단
    if not hard_constraint_check(state["task"], response.text):
        return {"constitution_passed": False, "final_response": None}

    # 2단: Soft gate — LLM 의미 판단
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
