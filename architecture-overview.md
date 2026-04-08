# AG-Forge Architecture Overview

---

## Part 1: 5-Layer Brain Architecture

### 1. 전두엽 (Prefrontal Cortex) - `brain.md`

**역할**: 최고 의사결정 센터
- 모든 하부 계층(좌뇌/우뇌/소뇌/해마)의 요약본을 실시간 수집
- 최종 응답 방향 설정
- 모순 감지 및 해결 로직

**갱신 주기**: 실시간 (매 작업마다)  
**용량 한계**: 20KB (초과 시 소뇌로 요청)  
**KV 캐싱**: ✅ 활성화 (입력 비용 90% 절감)

```yaml
brain.md:
  purpose: "모든 하부 정보의 통합점"
  contains:
    - current_task_state: "현재 작업 상태"
    - left_brain_summary: "좌뇌 핵심 요약 (코딩 패턴)"
    - right_brain_summary: "우뇌 핵심 요약 (UX 결정)"
    - cerebellum_action: "소뇌에서 전달한 즉각 액션"
    - memory_context: "해마 Vector RAG 검색 결과"
  update_trigger: "매 작업 타입 변화"
  cache_strategy: "KV 캐싱 고정 (문맥 유지)"
```

---

### 2. 좌뇌 (Left Brain) - `logic_rb.md`

**역할**: 논리/기술 처리  
- Ruby 코어 알고리즘, 수학적 계산
- BOQ 산식, 데이터베이스 설계, 아키텍처 결정  
- 코드 패턴 및 성능 최적화

**갱신 주기**: 코딩 작업 시 (매 30분)  
**용량 한계**: 40KB (초과 시 해마로 이관)  
**전용 모델**: Claude 3.5 Sonnet (프리미엄 추론)  
**Thinking Budget**: 높음 (5000+ tokens)

```yaml
logic_rb.md:
  purpose: "알고리즘 및 기술적 결정 기록"
  contains:
    - coding_patterns: "Ruby/Rails 패턴 라이브러리"
    - boq_formulas: "비용 산식 및 계산 로직"
    - db_schemas: "데이터베이스 설계 결정"
    - performance_notes: "최적화 벤치마크"
  router_priority: "complex_tasks, math_heavy, db_design"
  model_hint: "claude-3-5-sonnet"
```

---

### 3. 우뇌 (Right Brain) - `emotion_ui.md`

**역할**: 감성/UX 처리  
- 사용자 경험, 디자인 감각
- 인터페이스 직관성, 마이크로 카피
- 시각적 계층, 색상 이론, 감정적 공감

**갱신 주기**: 디자인 작업 시 (매 1시간)  
**용량 한계**: 40KB (초과 시 해마로 이관)  
**전용 모델**: Claude 3.5 Haiku (빠르고 경제적)  
**Thinking Budget**: 낮음-중간 (1000-2000 tokens)

```yaml
emotion_ui.md:
  purpose: "UX/디자인 결정 및 감성 맥락"
  contains:
    - design_principles: "프로젝트 디자인 원칙"
    - user_personas: "사용자 페르소나"
    - interaction_patterns: "상호작용 패턴"
    - accessibility_notes: "접근성 체크리스트"
  router_priority: "ui_design, copy_writing, user_research"
  model_hint: "claude-3-5-haiku"
```

---

### 4. 소뇌 (Cerebellum) - `judgment.md` (Router Agent)

**역할**: 즉각적 판단 & 모델 라우팅  
- 작업 난이도 1차 판별 (Simple/Medium/Complex)
- 좌뇌/우뇌 모델 선택 & Thinking Budget 동적 할당
- 오류 감지 및 즉시 수정

**갱신 주기**: 실시간 (매 작업)  
**용량 한계**: 10KB (매우 경량)  
**특이점**: **단순 markdown이 아닌 라우터 에이전트로 격상**

```yaml
judgment.md (Router Agent):
  purpose: "지능형 모델 라우터 & 예산 할당"
  logic:
    - if task_type == "ui_fix" || "copy_edit":
        route_to: "claude-3-5-haiku"
        thinking_budget: 500
        latency_priority: "low"
    - elif task_type == "algorithm" || "db_design":
        route_to: "claude-3-5-sonnet"
        thinking_budget: 5000
        cost_priority: "quality"
    - elif task_type == "decision_making":
        route_to: "gpt-4o-thinking" (if available)
        thinking_budget: 10000
        resource_priority: "unlimited"
  
  error_detection:
    - hallucination_check: "산출물이 문서와 모순되는가?"
    - token_overflow_check: "예산을 초과했는가?"
    - circular_logic_check: "좌뇌/우뇌가 루프를 도는가?"
```

---

### 5. 해마/도서관 (Hippocampus/Archive) - `library.md` + Vector DB

**역할**: 장기 저장소 & 의미 기반 검색  
- 용량 초과 시 자동 이관 (40~50KB 트리거)
- **Vector Embedding** 기반 Semantic Search  
- Agentic RAG로 필요한 기억만 검색 (토큰 낭비 0원)

**갱신 주기**: 주 1회 (자동 압축)  
**저장소 구조**:
  - `library-logic/` (좌뇌 기억: 알고리즘 패턴)
  - `library-emotion/` (우뇌 기억: 디자인 사례)
  - `library-decisions/` (소뇌 기억: 과거 선택)

```yaml
library_architecture:
  storage_layer: "Markdown + Vector DB (Redis or Pinecone)"
  
  markdown_storage:
    - library-logic.md    # 압축된 좌뇌 기억
    - library-emotion.md  # 압축된 우뇌 기억  
    - library-decisions.md # 압축된 소뇌 기억
  
  vector_db_layer:
    provider: "Redis (self-hosted) or Pinecone (managed)"
    embedding_model: "text-embedding-3-small (OpenAI)"
    chunk_size: 500
    overlap: 50
    similarity_threshold: 0.75
  
  agentic_rag:
    query_flow:
      - 1. 사용자 쿼리 받음
      - 2. 벡터 임베딩 생성
      - 3. Vector DB 시멘틱 서치 (Top 3)
      - 4. 해당 문서만 불러오기
      - 5. 통합 응답 생성
    cost_impact: "토큰 낭비 0원 (정확한 기억 검색)"
    latency: "< 200ms (Vector DB 쿼리)"
```

---

## Part 2: Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자 요청 입력                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  소뇌 (Router Agent)  │ ◄── Judgment.md
                    │  작업 난이도 판별    │
                    └──────────┬───────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
    ┌───────▼─────────┐ ┌──────▼──────┐ ┌───────▼────────┐
    │ 간단 (Simple)   │ │ 중간 (Mid)  │ │ 복잡 (Complex) │
    └───────┬─────────┘ └──────┬──────┘ └───────┬────────┘
            │                  │                 │
            ▼                  ▼                 ▼
    Haiku Model         Sonnet Model      Sonnet + Thinking
    Thinking: 500      Thinking: 2000    Thinking: 5000+
            │                  │                 │
            └──────────────────┼─────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
    ┌───────▼─────────┐ ┌──────▼──────┐ ┌───────▼────────┐
    │ 우뇌 로드      │ │  좌뇌 로드  │ │  과거 기억 로드 │
    │ (emotion_ui.md)│ │(logic_rb.md)│ │(Vector RAG)    │
    │ KV 캐싱 ✅     │ │ KV 캐싱 ✅ │ │ Semantic Search│
    └───────┬─────────┘ └──────┬──────┘ └───────┬────────┘
            │                  │                 │
            └──────────────────┼─────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   전두엽 (Brain.md)   │
                    │   최종 결정 & 응답    │
                    │   KV 캐싱 ✅        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  관측성 레이어       │
                    │  (LangSmith/OTel)    │
                    │  - 토큰 사용量       │
                    │  - 모델 라우팅 로그  │
                    │  - 비용 실시간 계산  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  용량 초과 감지?     │
                    └──────────┬───────────┘
                          YES  │  NO
                               │
               ┌───────────────┼───────────────┐
               │               │               │
               ▼               ▼               ▼
        ┌─────────────┐  (응답 반환)  ┌──────────────┐
        │ Vector DB로 │            │ 다음 작업 대기│
        │ 자동 이관  │            └──────────────┘
        │(압축후)    │
        └─────────────┘
```

---

## Part 3: 계층별 데이터 분류 자동화

AI가 생성한 모든 산출물은 자동으로 분류되어 저장됩니다:

```
코드 생성 → logic_rb.md (좌뇌)
UI/디자인 → emotion_ui.md (우뇌)
버그 수정 → judgment.md (소뇌)  
과거 패턴 → Vector DB (해마)
최종 결정 → brain.md (전두엽)
```

---

## Part 4: 계층 간 하이어라키 (Hierarchy) 구현

**실시간 업데이트 흐름:**

1️⃣ **작업 실행** → 좌뇌/우뇌 각각 산출물 생성  
2️⃣ **소뇌 제어** → 산출물 검증 & 오류 감지  
3️⃣ **전두엽 통합** → 모든 정보 취합 & 최종 응답 구성  
4️⃣ **관측성 기록** → 전체 작업 흐름 추적

**예시:**

```
사용자: "이 알고리즘 최적화할 수 있어?"

↓ 소뇌 판단: "복잡한 작업" → Sonnet + Thinking 5000 할당

↓ 좌뇌 실행: performance_notes.md에 최적화 분석 기재

↓ 소뇌 검증: "출력이 logic_rb.md의 패턴과 일치하는가?"

↓ 전두엽 통합: 전체 응답 구성 (brain.md 업데이트)

↓ 관측성 기록: 토큰 2340 사용, 비용 $0.0234, Sonnet 모델
```

---

## Summary

| 계층 | 파일 | 역할 | 모델 | 캐싱 |
|------|------|------|------|------|
| 전두엽 | brain.md | 최종 결정 | Any (로직) | ✅ KV |
| 좌뇌 | logic_rb.md | 알고리즘 | Sonnet | ✅ KV |
| 우뇌 | emotion_ui.md | UX/디자인 | Haiku | ✅ KV |
| 소뇌 | judgment.md | 라우터 에이전트 | Router Logic | N/A |
| 해마 | Vector DB + library.md | 기억 저장소 | RAG | ✅ Vector |

**다음 문서**: `technical-guidelines.md` (4가지 기술적 통제 장치)
