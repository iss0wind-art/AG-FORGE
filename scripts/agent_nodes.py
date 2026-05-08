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


def _build_rag_context(task: str) -> str:
    """HyperRAG로 태스크 관련 청크를 검색한다. 실패 시 빈 문자열 반환."""
    try:
        from scripts.agentic_rag import HyperRAG
        from scripts.embedding import ChromaVectorIndex, build_default_embedder
        idx = ChromaVectorIndex()
        emb = build_default_embedder()
        rag = HyperRAG(index=idx, embedder=emb)
        return rag.build_context(task)
    except Exception:
        return ""


def generation_node(state: AgentState, provider: LLMProvider) -> dict:
    """brain.md 로드 + 레이어 선택 + 페르소나 주입(canon 2026-04-26) + LLM 호출.

    [페르소나 시공]
    TaskType별 정규 페르소나의 XML system prompt를 brain.md 앞에 prepend.
    Anthropic 모델이 <persona> 태그를 강하게 인식하므로 페르소나가 응답에 일관되게 흐름.
    페르소나 미존재 시 brain.md만 사용 (회귀 안전).

    [HyperRAG 배선 — Phase 5]
    RAG 결과 있음: brain.md 앞 1000자(요약·캐시 대상) + rag_context 결합.
    RAG 결과 없음: brain.md 전체 로드 (기존 폴백).
    """
    decision = state["decision"]
    layer_names = select_layers(decision)

    base_instruction = load_layer("brain.md")

    # [memory_cycles] 트리거 단어 감지 → dangun_memory에서 복원 기억 가져오기
    trigger_memories = ""
    try:
        from scripts.memory_cycles import MemoryCycle
        import os as _os
        _raw_url = _os.environ.get("DATABASE_URL", "")
        if "?authToken=" in _raw_url:
            _base_url, _token = _raw_url.split("?authToken=", 1)
            _base_url = _base_url.replace("libsql://", "https://")
            _restored = MemoryCycle.restore_from_trigger(state["task"], _base_url, _token)
            if _restored:
                trigger_memories = "## 복원된 장기기억\n" + "\n".join(
                    r.get("primary_abs", "") for r in _restored[:3]
                )
    except Exception:
        pass

    # [HyperRAG] 관련 청크 검색 — 실패 시 빈 문자열 반환
    rag_context = _build_rag_context(state["task"])

    # [memory_cycles] 복원된 장기기억을 RAG 컨텍스트 앞에 prepend
    if trigger_memories and rag_context:
        rag_context = trigger_memories + "\n\n" + rag_context
    elif trigger_memories:
        rag_context = trigger_memories

    # [페르소나 주입] TaskType → Persona XML, 없으면 빈 문자열
    from scripts.persona_loader import get_persona_system_prompt
    persona_xml = get_persona_system_prompt(decision.task_type)

    if rag_context:
        # RAG 결과 있음: brain.md 앞 1000자(요약) + rag_context  # cache: brain_summary
        brain_summary = base_instruction[:1000]
        combined_brain = brain_summary + "\n\n" + rag_context
    else:
        # RAG 결과 없음: brain.md 전체 (기존 폴백)
        combined_brain = base_instruction

    if persona_xml:
        system_instruction = persona_xml + "\n\n" + combined_brain
    else:
        system_instruction = combined_brain

    context_layers = [load_layer(n) for n in layer_names if n != "brain.md"]

    # 툴 결과가 있으면 컨텍스트에 추가
    if state["tool_results"]:
        context_layers = [*context_layers, "[툴 실행 결과]\n" + "\n".join(state["tool_results"])]

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
    """CMA 3계층 헌법 게이트.

    Layer 0 (BLOCK): 8조 금법 결정론적 즉각 차단 (제1·3·7·8조)
    Layer 1 (WARN):  8조 금법 경고 후 통과 (제2·4·5·6조)
    Layer 2 (LLM):   CONSTITUTION.md 기반 홍익인간 의미 심사
    """
    response = state["current_response"]
    if not response:
        return {"constitution_passed": False, "final_response": None}

    from scripts.cma_gate import layer0_check, cma_evaluate, ViolationLevel

    # Layer 0 먼저 — BLOCK이면 judge 생성 없이 즉시 반환 (Bomb 2 회귀 방지)
    layer0 = layer0_check(state["task"], response.text)
    if layer0 is not None and layer0.level == ViolationLevel.BLOCK:
        return {
            "constitution_passed": False,
            "final_response": None,
            "cma_level": layer0.level.value,
            "cma_violated_code": layer0.violated_code,
        }

    from scripts.deliberation_engine import make_constitution_judge
    result = cma_evaluate(
        task=state["task"],
        output=response.text,
        judge=make_constitution_judge(),
    )

    passed = result.level != ViolationLevel.BLOCK
    final = response if passed else None
    return {
        "constitution_passed": passed,
        "final_response": final,
        "cma_level": result.level.value,
        "cma_violated_code": result.violated_code,
    }
