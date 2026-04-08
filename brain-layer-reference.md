# AG-Forge: Brain Layer Reference

각 계층의 역할, 입출력 형식, 업데이트 규칙을 상세히 기술합니다.  
구현 시 이 문서를 기준으로 각 `.md` 파일의 스키마를 설계합니다.

---

## Layer 1: 전두엽 (Prefrontal Cortex) — `brain.md`

**역할**: 최고 의사결정 센터. 모든 하부 계층 요약을 통합해 최종 응답을 구성합니다.

### 파일 스키마

```markdown
# brain.md

## 현재 작업 상태
- task_id: {UUID}
- task_type: coding | design | planning | debug
- task_started: {ISO 8601}
- active_layer: left_brain | right_brain | both

## 좌뇌 요약 (logic_rb.md 최신 핵심)
{좌뇌가 마지막 작업에서 결정한 핵심 패턴 1-3줄}

## 우뇌 요약 (emotion_ui.md 최신 핵심)
{우뇌가 마지막 작업에서 결정한 UX 원칙 1-3줄}

## 소뇌 마지막 액션 (judgment.md)
- routed_to: haiku | sonnet | sonnet+thinking
- thinking_budget_used: {number}
- error_flags: none | hallucination | token_overflow | circular_logic

## 해마 검색 결과
- query: {마지막 RAG 쿼리}
- retrieved_chunks: {개수}
- relevance_score: {0.0-1.0}
```

### 업데이트 규칙

| 트리거 | 업데이트 내용 |
|--------|-------------|
| 작업 타입 변화 | active_layer, task_type 갱신 |
| 좌뇌 작업 완료 | 좌뇌 요약 3줄 갱신 |
| 우뇌 작업 완료 | 우뇌 요약 3줄 갱신 |
| 소뇌 라우팅 결정 | error_flags, routed_to 갱신 |
| RAG 검색 완료 | 해마 검색 결과 갱신 |

### 용량 제한

- **최대**: 20KB
- **초과 시**: 소뇌에 요약 압축 요청 → 해마로 이관
- **KV 캐싱**: `ephemeral` (TTL 5분)

---

## Layer 2: 좌뇌 (Left Brain) — `logic_rb.md`

**역할**: 논리/기술 처리 전담. 코드 패턴, 알고리즘, DB 설계를 누적합니다.

### 파일 스키마

```markdown
# logic_rb.md

## Ruby/Rails 패턴 라이브러리
### [패턴명]
- 문제: {해결한 문제}
- 솔루션: {패턴 요약}
- 코드 참조: {파일명:줄번호 또는 스니펫}
- 적용 일자: {YYYY-MM-DD}

## BOQ 산식 & 계산 로직
### [산식명]
- 공식: {수식}
- 변수 정의: {변수: 단위}
- 검증 사례: {테스트 케이스}

## DB 설계 결정
### [테이블/스키마명]
- 결정: {설계 선택}
- 근거: {이유}
- 트레이드오프: {포기한 것}

## 성능 최적화 메모
### [최적화 항목]
- Before: {기존 성능}
- After: {개선 성능}
- 방법: {기술}
```

### 데이터 분류 규칙

AI가 생성하거나 결정한 아래 항목은 **자동으로 `logic_rb.md`에 기록**합니다:

- Ruby/Rails 코드 생성
- 수학적 계산, 알고리즘 설계
- DB 스키마, 마이그레이션
- API 엔드포인트 설계
- 성능 벤치마크, 프로파일링 결과

### 용량 제한

- **최대**: 40KB (~50KB 도달 시 아카이브 트리거)
- **아카이브 대상**: 30일 이상 미참조 항목
- **전용 모델**: claude-sonnet-4-6
- **Thinking Budget**: 5,000+ tokens

---

## Layer 3: 우뇌 (Right Brain) — `emotion_ui.md`

**역할**: 감성/UX 처리 전담. 디자인 원칙, 사용자 경험, 마이크로 카피를 누적합니다.

### 파일 스키마

```markdown
# emotion_ui.md

## 디자인 원칙
- primary_color: {hex}
- typography: {font-family, scale}
- spacing_unit: {px}
- border_radius: {px}
- motion_duration: {ms}

## 사용자 페르소나
### [페르소나명]
- 특성: {설명}
- 주요 불편: {pain point}
- 기대 행동: {expected behavior}

## 상호작용 패턴
### [패턴명]
- 상황: {언제 사용}
- 컴포넌트: {UI 요소}
- 피드백: {사용자가 받는 응답}

## 마이크로 카피 결정
### [컨텍스트]
- 채택: "{최종 카피}"
- 기각: "{기각된 옵션}" (이유: {이유})

## 접근성 체크리스트
- [ ] WCAG 2.1 AA 색상 대비
- [ ] 키보드 내비게이션
- [ ] 스크린 리더 라벨
- [ ] 포커스 표시
```

### 데이터 분류 규칙

아래 항목은 **자동으로 `emotion_ui.md`에 기록**합니다:

- UI 컴포넌트 설계/수정
- UX 문구(마이크로 카피) 결정
- 디자인 시스템 결정
- 사용자 리서치 인사이트
- 접근성 개선 사항

### 용량 제한

- **최대**: 40KB
- **전용 모델**: claude-haiku-4-5-20251001
- **Thinking Budget**: 1,000-2,000 tokens

---

## Layer 4: 소뇌 (Cerebellum) — `judgment.md` (Router Agent)

**역할**: 즉각적 판단 & 모델 라우팅. 단순 마크다운이 아닌 **실행 가능한 라우터 로직**입니다.

### 라우팅 규칙 테이블

| 작업 타입 | 판별 키워드 | 모델 | Thinking Budget | 우선 로드 레이어 |
|----------|------------|------|----------------|----------------|
| UI 수정 | fix, typo, color, style, copy | haiku-4-5 | 500 | emotion_ui.md |
| 기획/리서치 | plan, research, strategy, why | sonnet-4-6 | 2,000 | brain.md |
| 알고리즘 | algorithm, optimize, calculate, formula | sonnet-4-6 | 5,000 | logic_rb.md |
| DB 설계 | schema, migration, query, index | sonnet-4-6 | 5,000 | logic_rb.md |
| 복합 의사결정 | architect, design system, tradeoff | sonnet-4-6 | 10,000 | brain.md + both |

### 오류 감지 체크리스트 (매 작업 후 실행)

```python
ERROR_CHECKS = [
    {
        "name": "hallucination_check",
        "trigger": "산출물이 logic_rb.md 또는 emotion_ui.md의 기존 결정과 모순되는가?",
        "action": "불일치 항목을 brain.md에 플래그 → 사용자에게 확인 요청"
    },
    {
        "name": "token_overflow_check",
        "trigger": "thinking_budget_used > 할당 예산의 90%",
        "action": "작업 분할 제안 → 새 세션으로 이관"
    },
    {
        "name": "circular_logic_check",
        "trigger": "좌뇌/우뇌가 동일한 결정을 3회 이상 반복",
        "action": "루프 중단 → brain.md에 교착 상태 기록 → 사용자 개입 요청"
    },
    {
        "name": "layer_size_check",
        "trigger": "logic_rb.md 또는 emotion_ui.md가 40KB 초과",
        "action": "자동 아카이빙 스크립트 실행 (auto_archive.py)"
    }
]
```

### 용량 제한

- **최대**: 10KB (경량 유지 필수)
- **업데이트**: 매 작업마다 라우팅 결정 1줄 로그

---

## Layer 5: 해마/도서관 (Hippocampus) — Vector DB + `library-*.md`

**역할**: 장기 기억 저장소. 용량을 초과한 좌뇌/우뇌 데이터를 벡터 임베딩으로 보관합니다.

### 저장소 구조

```
library/
├── library-logic.md       # 압축된 좌뇌 기억 (텍스트 요약)
├── library-emotion.md     # 압축된 우뇌 기억 (텍스트 요약)
├── library-decisions.md   # 소뇌 주요 결정 이력
└── vector-index/          # Vector DB 임베딩 (실제 검색 대상)
    ├── logic-chunks/
    ├── emotion-chunks/
    └── decision-chunks/
```

### 아카이브 트리거 조건

| 레이어 | 트리거 임계값 | 아카이브 대상 |
|--------|-------------|-------------|
| logic_rb.md | 40KB 초과 | 30일 미참조 항목 |
| emotion_ui.md | 40KB 초과 | 30일 미참조 항목 |
| brain.md | 20KB 초과 | 완료된 작업 요약 |

### RAG 검색 흐름

```
1. 사용자 쿼리 수신
2. text-embedding-3-small으로 임베딩 생성
3. Vector DB 시맨틱 서치 (top_k=3, threshold=0.75)
4. 관련 청크만 추출 (평균 200 tokens)
5. brain.md의 "해마 검색 결과" 섹션에 기록
6. LLM 컨텍스트에 주입
```

---

## 계층 간 통신 규약

```
사용자 요청
    ↓
[소뇌] 난이도 판별 → 모델 & 예산 결정
    ↓
[해마] RAG 검색 → 관련 과거 기억 주입
    ↓
[좌뇌 OR 우뇌] 전문 작업 실행
    ↓
[소뇌] 오류 체크 4종
    ↓
[전두엽] 최종 응답 통합
    ↓
[관측성 레이어] 토큰/비용/경로 기록
    ↓
응답 반환
```

**다음 문서**: `cost-optimization-guide.md`
