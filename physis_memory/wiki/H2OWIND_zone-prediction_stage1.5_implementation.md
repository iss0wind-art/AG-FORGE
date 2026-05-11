---
created: 2026-05-09
outcome_score: 0.0
ref_count: 2
tags:
- h2owind
- 2지국
- zone-prediction
- stage1.5
- ai-augmentation
- 이순신
- phase1
type: wiki
---

# H2OWIND_zone-prediction_stage1.5_implementation

# Stage 1.5 — AI 보조 추론 (Phase 1 구현 완료, 2026-05-09)

[[H2OWIND_docs_ZONE_PREDICTION_BLUEPRINT]]의 후속 진화. 이순신 지국이 본영의 "예측·추론에도 AI가 한 번 더 판단에 도움" 칙령(2026-05-09)을 받아 1차 구현.

## 핵심 의도

`ZonePredictionEngine.runStage1`은 "타설일 D-7~D-1 평일 안에 작업 가능한 앵커 후보"를 결정론적으로 찾는다. 후보가 정확히 1개면 INSERT, 0개면 noMatch, **2개 이상이면 그냥 ambiguous 카운트만 증가시키고 Stage 2로 떠넘겼다.** Stage 1.5는 이 ambiguous 자리에 끼어드는 AI 보조 단계.

## 7개 추론 지점 카탈로그 (전체 로드맵)

룰 기반 엔진에서 AI 보조가 가치 있는 지점들:

| # | 위치 | 룰의 한계 | Phase |
|:-:|---|---|:-:|
| A | `ZonePredictionEngine.ts:448-462` Stage 1 ambiguous | 카운트만, Stage 2 떠넘김 | **1 ✅** |
| B | `ZonePredictionEngine.ts:650-665` Stage 2 전환구간 (`prevDong ≠ nextDong`) | 무조건 앞쪽 동, conf 0.60 고정 | 2 |
| C | `ZonePredictionEngine.ts:666-671` Stage 2 단방향 앵커 | 한쪽 복사, conf 0.65 | 2 |
| D | `PourAnchorParser.ts:101-105` Tier B (동만 있고 층 빠짐) | 호출 측 보간 미구현 | 3 |
| E | `topdownSchedule.ts:103` `cycleDays = max(formwork, 7)` | 연휴·동절기·옥탑층 무시 | 4 |
| F | `topdownSchedule.ts:152-160` TopDown 결과 | 리스크 코멘트 없음 | 4 |
| G | `gantt-import/route.ts` 공정표 동기화 | 변경 영향 분석 없음 | 5 |

## Phase 1 구현물 (코드 위치)

- `lib/ai/zonePredictionAI.ts` — 피지수 1순위 → Gemini 1.5 Flash 폴백, JSON 강제 스키마
- `lib/ZonePredictionEngine.ts` `runStage1_5()` 신규
- `Stage1Report.ambiguousItems: Stage1AmbiguousItem[]` 필드 추가 (Stage 1이 ambiguous를 외부에 노출)
- `db/schema.ts` `zonePredictions` 4개 컬럼 추가: `status`, `aiAssisted`, `aiModel`, `aiReason`
- `app/api/zone-prediction/stage1_5/route.ts` 실행 트리거
- `app/api/zone-prediction/pending-review/route.ts` (GET) + `decide/route.ts` (POST)
- `app/components/ZonePredictionPendingReview.tsx` — 승인 큐 UI ("AI 예측 후보" 카드)
- `ZonePredictionTab.tsx`에 통합 (구간예측 탭 하단)

## 결정론 보존 5원칙 (이번 작업의 헌법)

1. **AI는 룰을 못 뒤집는다.** Stage 1.5는 Stage 1이 답을 못 낸 ambiguous 항목에만 개입. 룰이 결정한 INSERT는 절대 AI가 덮어쓰지 못함.
2. **신뢰도 cap.** AI 결과 conf는 최대 0.78 (룰 기반 최대 pour=0.92, Stage2 양쪽일치=0.85 미만).
3. **status 분리.** `auto-confirmed` ⇄ `pending-review` 두 단계. Stage 2 보간/Stage 3 검증/리포트 export는 모두 `auto-confirmed`만 본다 — pending이 다음 단계로 새지 않음.
4. **임계치 0.65.** Stage 2 단방향 앵커(0.65)와 동일 기준으로 "자동 사용 가능" 여부 결정. 미만은 사람 승인 큐.
5. **추적성.** 모든 AI INSERT는 `aiAssisted=true`, `aiModel`, `aiReason` 컬럼으로 식별 가능.

## Stage 1.5 동작 흐름

1. `runStage1({ dryRun: true, skipInfaceSync: true })` — INSERT 안 하고 ambiguous만 수집
2. `ambiguousItems`의 logId들로 `dailyWorkLogs.content` 일괄 로드
3. 각 항목에 대해 `resolveAmbiguous()` 호출 (피지수 → Gemini 폴백)
4. 응답의 `chosenDong/chosenFloor`가 후보 목록에 실제 있는지 검증 (환각 방어)
5. conf ≥ 0.65 → `status='auto-confirmed'` INSERT (Stage 2/3에서도 활용)
6. conf < 0.65 → `status='pending-review'` INSERT (UI에서 사람 승인)

## 향후 진화 메모

- Phase 2 (Stage 2.5): 전환구간 + 단방향 앵커. 인페이스 출퇴근 인원 비율을 추가 입력으로.
- Phase 3 (Tier B 보간): `parsed-suggestions`에 `tierB_ai_suggestions` 통합.
- Phase 4 (TopDown 리스크): 일정은 안 바꾸고 자연어 리스크 노트만 첨부.
- Phase 5 (Gantt diff): 변경 영향 자연어 리포트.

각 Phase는 같은 5원칙 위에서 진행. 룰 깨면 Phase 자체 무산.


## 연결

- [[홍익인간]]
