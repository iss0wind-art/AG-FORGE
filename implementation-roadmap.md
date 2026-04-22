# AG-Forge: 구현 로드맵

**리팀장(최태산) 주도 단계별 구현 계획**  
**목표**: 4주 내 MVP 완료 → 방부장 최종 결재

---

## 전제 조건 (착수 전 확인)

- [ ] Anthropic API 키 발급 (claude-sonnet-4-6, claude-haiku-4-5 접근 권한)
- [ ] OpenAI API 키 발급 (text-embedding-3-small)
- [ ] Pinecone 계정 생성 (파일럿: 무료 플랜)
- [ ] Python 3.11+ 환경
- [ ] LangSmith 계정 (무료 플랜으로 시작)

---

## Phase 1: 기반 구조 (Week 1)

**목표**: 뇌 계층 파일 초기화 + 기본 KV 캐싱 검증

### Day 1-2: 뇌 파일 초기화

```bash
# 프로젝트 구조 생성
mkdir -p ag-forge/{brain,library,scripts,tests}

# 뇌 계층 파일 생성
touch ag-forge/brain/brain.md
touch ag-forge/brain/logic_rb.md
touch ag-forge/brain/emotion_ui.md
touch ag-forge/brain/judgment.md
touch ag-forge/library/library-logic.md
touch ag-forge/library/library-emotion.md
touch ag-forge/library/library-decisions.md
```

`brain-layer-reference.md`의 스키마를 기준으로 각 파일 초기 구조를 작성합니다.

### Day 3-4: KV 캐싱 연동

`technical-guidelines.md`의 `claude_kv_cache.py` 기반으로 구현합니다.

```python
# scripts/brain_loader.py
import anthropic
from pathlib import Path

BRAIN_DIR = Path("ag-forge/brain")

def load_brain_with_cache(task: str) -> anthropic.types.Message:
    client = anthropic.Anthropic()
    
    brain = (BRAIN_DIR / "brain.md").read_text(encoding="utf-8")
    logic = (BRAIN_DIR / "logic_rb.md").read_text(encoding="utf-8")
    emotion = (BRAIN_DIR / "emotion_ui.md").read_text(encoding="utf-8")
    
    return client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {"type": "text", "text": brain,
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": logic,
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": emotion,
             "cache_control": {"type": "ephemeral"}},
        ],
        messages=[{"role": "user", "content": task}]
    )
```

### Day 5: Phase 1 검증

```python
# tests/test_phase1.py
def test_kv_cache_hit():
    """동일 파일을 2회 호출 시 캐시 히트 확인"""
    r1 = load_brain_with_cache("테스트 쿼리")
    r2 = load_brain_with_cache("테스트 쿼리 2")
    
    assert r2.usage.cache_read_input_tokens > 0, "캐시 히트 없음"
    print(f"캐시 히트율 확인: {r2.usage.cache_read_input_tokens} tokens 절감")
```

**Phase 1 완료 기준**: 캐시 히트율 >70% 달성

---

## Phase 2: 해마 구현 (Week 2)

**목표**: Vector DB 연동 + Agentic RAG 작동 확인

### Day 6-7: Pinecone 설정

```python
# scripts/setup_vector_db.py
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

pc.create_index(
    name="ag-forge-memory",
    dimension=1536,          # text-embedding-3-small 출력 차원
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1")
)
```

### Day 8-9: 임베딩 파이프라인

`technical-guidelines.md`의 `embedding.py`와 `agentic_rag.py`를 구현합니다.

기존 `library-logic.md`, `library-emotion.md` 내용을 마이그레이션합니다:

```bash
python scripts/migrate_to_vector.py \
  --source ag-forge/library/library-logic.md \
  --category logic

python scripts/migrate_to_vector.py \
  --source ag-forge/library/library-emotion.md \
  --category emotion
```

### Day 10: Phase 2 검증

```python
# tests/test_phase2.py
def test_rag_retrieval():
    """과거 기억 검색 정확도 확인"""
    rag = AgenticRAG(...)
    results = rag.search("Ruby on Rails 최적화 패턴", top_k=3)
    
    assert len(results) == 3, "Top-3 결과 미반환"
    assert all(r["score"] > 0.75 for r in results), "유사도 임계값 미달"
    
    # 토큰 효율 확인
    token_count = count_tokens("\n".join(results))
    assert token_count < 500, f"RAG 결과가 너무 큼: {token_count} tokens"
```

**Phase 2 완료 기준**: RAG 검색 정확도 >80%, 결과 토큰 <500

---

## Phase 3: 소뇌 라우터 (Week 3)

**목표**: 지능형 모델 라우터 + Thinking Budget 동적 할당

### Day 11-13: 라우터 구현

```python
# scripts/router_agent.py
from dataclasses import dataclass
from enum import Enum

class TaskComplexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    DECISION = "decision"

@dataclass
class RoutingDecision:
    model: str
    thinking_budget: int
    primary_layer: str

ROUTING_TABLE = {
    TaskComplexity.SIMPLE: RoutingDecision(
        model="claude-haiku-4-5-20251001",
        thinking_budget=500,
        primary_layer="emotion_ui.md"
    ),
    TaskComplexity.MEDIUM: RoutingDecision(
        model="claude-sonnet-4-6",
        thinking_budget=2000,
        primary_layer="brain.md"
    ),
    TaskComplexity.COMPLEX: RoutingDecision(
        model="claude-sonnet-4-6",
        thinking_budget=5000,
        primary_layer="logic_rb.md"
    ),
    TaskComplexity.DECISION: RoutingDecision(
        model="claude-sonnet-4-6",
        thinking_budget=10000,
        primary_layer="brain.md"
    ),
}

KEYWORD_MAP = {
    TaskComplexity.SIMPLE: ["fix", "typo", "color", "style", "copy", "ui", "수정"],
    TaskComplexity.MEDIUM: ["plan", "research", "strategy", "기획", "분석"],
    TaskComplexity.COMPLEX: ["algorithm", "optimize", "schema", "migration", "알고리즘"],
    TaskComplexity.DECISION: ["architect", "tradeoff", "system design", "아키텍처"],
}

def classify_task(task: str) -> TaskComplexity:
    task_lower = task.lower()
    for complexity, keywords in KEYWORD_MAP.items():
        if any(kw in task_lower for kw in keywords):
            return complexity
    return TaskComplexity.MEDIUM  # 기본값

def route(task: str) -> RoutingDecision:
    complexity = classify_task(task)
    decision = ROUTING_TABLE[complexity]
    
    # judgment.md에 라우팅 기록
    log_routing_decision(task, complexity, decision)
    
    return decision
```

### Day 14-15: 오류 감지 + Phase 3 검증

```python
# tests/test_phase3.py
def test_routing_accuracy():
    """라우팅 정확도 검증 (20개 샘플)"""
    test_cases = [
        ("버튼 색상 수정", TaskComplexity.SIMPLE),
        ("DB 인덱스 최적화", TaskComplexity.COMPLEX),
        ("전체 아키텍처 결정", TaskComplexity.DECISION),
        # ... 17개 추가
    ]
    
    correct = sum(1 for task, expected in test_cases
                  if classify_task(task) == expected)
    accuracy = correct / len(test_cases)
    
    assert accuracy >= 0.9, f"라우팅 정확도 미달: {accuracy:.1%}"

def test_budget_guard():
    """Budget 초과 경보 작동 확인"""
    # ... 테스트 구현
```

**Phase 3 완료 기준**: 라우팅 정확도 >90%

---

## Phase 4: 관측성 + 자동 아카이빙 (Week 4)

**목표**: LangSmith 연동 + 자동 아카이빙 + 방부장 결재 준비

### Day 16-17: LangSmith 연동

```python
# scripts/observability.py
from langsmith import Client
from langsmith.run_helpers import traceable

ls_client = Client()

@traceable(name="AG-Forge Brain Request")
def traced_brain_request(task: str) -> dict:
    routing = route(task)
    rag_results = rag.search(task)
    response = load_brain_with_cache(task)
    
    return {
        "task": task,
        "model_used": routing.model,
        "thinking_budget": routing.thinking_budget,
        "cache_tokens_saved": response.usage.cache_read_input_tokens,
        "rag_chunks": len(rag_results),
        "total_cost_usd": calculate_cost(response.usage),
    }
```

### Day 18-19: 자동 아카이빙 크론 설정

`technical-guidelines.md`의 `auto_archive.py`를 배포합니다.

```bash
# Linux/Mac: cron 등록
echo "0 0 * * * python /path/to/auto_archive.py >> /var/log/ag-forge-archive.log 2>&1" | crontab -

# Windows: 작업 스케줄러 (PowerShell)
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\ag-forge\scripts\auto_archive.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 00:00
Register-ScheduledTask -TaskName "AG-Forge Auto Archive" -Action $action -Trigger $trigger
```

### Day 20: 최종 통합 테스트 + 결재 준비

```python
# tests/test_integration.py
def test_full_pipeline():
    """전체 파이프라인 E2E 검증"""
    task = "사용자 대시보드의 로딩 속도를 최적화하고, UX 개선안도 제시해줘"
    
    # 1. 소뇌 라우팅
    routing = route(task)
    assert routing.model == "claude-sonnet-4-6"
    
    # 2. 해마 RAG 검색
    memories = rag.search(task)
    assert len(memories) > 0
    
    # 3. 뇌 계층 로드 (캐싱)
    response = load_brain_with_cache(task)
    assert response.usage.cache_read_input_tokens > 0
    
    # 4. 비용 확인
    cost = calculate_cost(response.usage)
    assert cost < 0.10, f"단일 요청 비용 초과: ${cost:.4f}"
    
    print(f"통합 테스트 통과: ${cost:.4f}/요청")
```

**Phase 4 완료 기준**: E2E 테스트 통과 + LangSmith 대시보드 정상 작동

---

## 방부장 최종 결재 체크리스트

Phase 4 완료 후 아래 항목의 **실측값**을 첨부하여 결재를 신청합니다.

| 항목 | 목표값 | 실측값 | 달성 여부 |
|------|-------|-------|---------|
| KV 캐시 히트율 | >70% | | |
| RAG 검색 정확도 | >80% | | |
| 라우팅 정확도 | >90% | | |
| 단일 요청 평균 비용 | <$0.05 | | |
| 월간 예상 비용 | <$400 | | |
| 평균 응답 레이턴시 | <2초 | | |
| E2E 테스트 통과율 | 100% | | |

모든 실측값이 목표를 달성했을 때만 결재를 신청하십시오.

---

## 의존성 그래프

```
Phase 1 (KV 캐싱)
    │
    ├── Phase 2 (Vector RAG) ── Phase 3에 RAG 컨텍스트 제공
    │
    ├── Phase 3 (라우터) ──────── Phase 2 완료 후 시작 가능
    │
    └── Phase 4 (관측성) ──────── Phase 1-3 모두 완료 후 통합
```

Phase 2와 Phase 3은 Phase 1 완료 후 **병렬 진행** 가능합니다.

---

**이전 문서**: `cost-optimization-guide.md`  
**돌아가기**: `README.md`
