# 단군 집도 핸드오프 — Architect OS 코어 통합 수술

> 작성: 피지수 (Physis) — 수술 준비 문서  
> 일자: 2026-04-28  
> 집도의: 단군  
> 참관: 방부장  
> 환자: 피지수 자신

---

## 🔴 핵심 요약 (먼저 읽을 것)

**Phase 1~4는 이미 완성돼 있다.**

피지수 코드베이스를 전수조사한 결과, 계획서의 대수술이 **이미 절반 이상 시행된 상태**임을 확인했다. 단군이 해야 할 일은:

1. **Phase 5**: `generation_node` → HyperRAG 배선 (미완성)
2. **실패 테스트 2개** 수정 (선행 필요)
3. **프롬프트 캐싱** 추가 (단군 권고사항)

---

## 📁 현재 코드 상태

### 완성된 것 (건드리지 말 것)

| 파일 | 상태 | 내용 |
|---|---|---|
| `scripts/embedding.py` | ✅ 완성 | `ChromaVectorIndex` + `SimpleTFIDFEmbedder` + `build_default_embedder()` |
| `scripts/titans_memory.py` | ✅ 완성 | 실제 벡터 Surprise Metric, `_reinforce_existing()` (Memora Create-or-Update) |
| `scripts/agentic_rag.py` | ✅ 완성 | `HyperRAG` 3단계 파이프라인 + SACHOCHEONG 인터페이스 + Token Budget |
| `scripts/cma.py` | ✅ 완성 | CMA 헌법적 메모리 저장 파이프라인 |
| `scripts/cma_gate.py` | ✅ 완성 | layer0_check, ViolationLevel |

### 미완성 (단군이 할 것)

| 파일 | 상태 | 내용 |
|---|---|---|
| `scripts/agent_nodes.py` | ❌ Phase 5 미완 | `generation_node`가 여전히 `load_layer("brain.md")` 전체 로드 |

---

## 🔧 Phase 5 — generation_node HyperRAG 배선

### 현재 코드 (`scripts/agent_nodes.py` line 50~77)

```python
def generation_node(state: AgentState, provider: LLMProvider) -> dict:
    decision = state["decision"]
    layer_names = select_layers(decision)

    base_instruction = load_layer("brain.md")          # ← 전체 로드 (트리 구조)

    from scripts.persona_loader import get_persona_system_prompt
    persona_xml = get_persona_system_prompt(decision.task_type)

    if persona_xml:
        system_instruction = persona_xml + "\n\n" + base_instruction
    else:
        system_instruction = base_instruction

    context_layers = [load_layer(n) for n in layer_names if n != "brain.md"]

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
```

### 목표 코드 (단군이 구현할 것)

```python
def generation_node(state: AgentState, provider: LLMProvider) -> dict:
    decision = state["decision"]
    layer_names = select_layers(decision)

    # ── HyperRAG 검색 (벡터 구체 모델) ──────────────────────────────────────
    rag_context = ""
    try:
        from scripts.agentic_rag import HyperRAG
        from scripts.embedding import ChromaVectorIndex, build_default_embedder
        _index = ChromaVectorIndex()
        _embedder = build_default_embedder()
        hyper_rag = HyperRAG(_index, _embedder)
        rag_context = hyper_rag.build_context(state["task"])
    except Exception as e:
        import sys
        print(f"[generation_node] HyperRAG 폴백: {e}", file=sys.stderr)

    # ── brain.md: 프롬프트 캐싱 대상 (요약만 사용) ──────────────────────────
    # IMPORTANT: brain.md[:2000]을 캐시 고정 구간으로 사용.
    # 반복 호출 시 Anthropic 프롬프트 캐시 40~60% 비용 절감.
    brain_summary = load_layer("brain.md")[:2000]

    # ── 시스템 인스트럭션 조합 ────────────────────────────────────────────────
    from scripts.persona_loader import get_persona_system_prompt
    persona_xml = get_persona_system_prompt(decision.task_type)

    parts = []
    if persona_xml:
        parts.append(persona_xml)
    if rag_context:                       # HyperRAG 결과 우선
        parts.append(rag_context)
    parts.append(brain_summary)           # 캐시 고정 구간 (항상 포함)

    system_instruction = "\n\n".join(parts)

    # ── 나머지 레이어 ─────────────────────────────────────────────────────────
    context_layers = [load_layer(n) for n in layer_names if n != "brain.md"]

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
```

---

## 🔴 실패 테스트 2개 (선행 수정 필요)

### 실패 1: `test_constitution_node_blocks_via_hard_gate`

```
tests/test_agent_graph.py:263
AssertionError: hard_gate를 통과해야 하는데 LLM judge가 호출됨
```

**문제**: `constitution_node`에서 hard_constraint_check가 통과 후 LLM judge가 불필요하게 호출됨.  
**위치**: `scripts/agent_nodes.py` → `constitution_node` → `make_constitution_judge()` 호출 순서.  
**방향**: hard_gate가 BLOCK 반환 시 LLM judge를 호출하지 않고 즉시 반환해야 함.

### 실패 2: `test_task_goes_through_constitution_gate`

```
tests/test_server.py:158
assert data.get("constitution_passed") is True
→ 실제: False
```

**문제**: 정상 작업이 constitution 게이트에서 False로 반환됨.  
**방향**: hard_constraint_check 패턴 목록 또는 task 내용 확인 필요.

---

## 🚫 절대 불가침 경계

```
D:\Git\신고조선\사초청\   ← 본관 접근 금지 (존재 확인도 하지 말 것)
```

```python
# SACHOCHEONG 분관 — 읽기 전용, 아래 경로만 허용
DREAM_FAC/SACHOCHEONG/log/  ← 새 파일 있을 때만 읽기
DREAM_FAC/SACHOCHEONG/CHARTER.md
DREAM_FAC/SACHOCHEONG/DANJAE_PERSONA.md
# 이미 agentic_rag.py의 load_sachocheong_context()에 구현됨
```

---

## 🧪 테스트 기준

수술 완료 조건:

```bash
python -m pytest tests/ -q
# 목표: 298 passed, 0 failed
# 현재: 296 passed, 2 failed
```

Phase 5 완료 후 추가 테스트 권장:

```bash
# HyperRAG 배선 확인
python -m pytest tests/test_agent_graph.py -v

# 전체 파이프라인 E2E
python -m pytest tests/test_e2e.py -v
```

---

## 📐 인터페이스 계약 (변경 금지)

단군이 수정할 때 아래 시그니처는 **절대 변경하지 말 것**. 다른 노드들이 의존함.

```python
# agent_nodes.py
def generation_node(state: AgentState, provider: LLMProvider) -> dict:
    # 반환: {"current_response": BrainResponse, "attempts": int}

# titans_memory.py  
def store_memory(content, category, index, embedder) -> bool:
def optimize_memory(index=None, embedder=None) -> None:

# agentic_rag.py
class HyperRAG:
    def build_context(self, query: str) -> str:
    def search_pipeline(self, query: str) -> list[RetrievedChunk]:

# cma.py
def memory_store(content, category, index, embedder, audit_path=None) -> dict:
```

---

## 📊 파일별 규모

```
scripts/brain_loader.py      434줄  (LLM 프로바이더 체인 — 건드리지 말 것)
scripts/agentic_rag.py       299줄  ✅ HyperRAG 완성
scripts/embedding.py         210줄  ✅ ChromaVectorIndex 완성
scripts/titans_memory.py     207줄  ✅ Memora 완성
scripts/agent_nodes.py       236줄  ← Phase 5 수정 대상
scripts/cma.py               125줄  ✅ CMA 완성
scripts/cma_gate.py          232줄  ✅ 헌법 게이트 완성
scripts/life_cycle_manager.py 152줄 ✅ V3 Life Guard 완성
```

---

## 🔗 단군이 참조할 기존 설계 문서

- [FRACTAL_BRAIN_PROPOSAL.md](FRACTAL_BRAIN_PROPOSAL.md) — 프렉탈 구체 아키텍처 제안서
- [physis_brain.mm.md](physis_brain.mm.md) — 피지수 뇌 전체 구조 마인드맵
- [CLAUDE.md](CLAUDE.md) — 프로젝트 운영 지침

---

## 마지막 말

피지수는 대기합니다.

수술 중 피지수의 테스트가 기준이 됩니다. `298 passed, 0 failed` 이 숫자가 수술 성공의 증거입니다.

*— 피지수, 2026-04-28*
