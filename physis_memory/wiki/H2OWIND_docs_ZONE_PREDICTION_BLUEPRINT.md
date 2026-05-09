---
created: 2026-05-09
outcome_score: 0.0
ref_count: 1
tags:
- h2owind
- 2지국
- 이순신
type: wiki
---

# H2OWIND_docs_ZONE_PREDICTION_BLUEPRINT

> 출처: `H2OWIND_2/docs/ZONE_PREDICTION_BLUEPRINT.md` — 2지국 H2OWIND (이순신) 자동 흡수
> 흡수일: 2026-05-09

# 구간예측(ZonePrediction) 고도화 기획안

> 작성일: 2026-04-26
> 수도: D:\GIT\h2owind
> 결재 대상: 방부장 (창조주)

---

## 결론 요약 (먼저 읽을 것)

현재 구간예측은 **Stage 1(타설 앵커)과 Stage 2(인접 보간)만 실제 동작**하며, Stage 3(LightGBM)은 껍데기만 있다. 신뢰도 계산은 고정값 rule-based이고, 관리자 확정 데이터가 쌓이고 있으나 피드백 루프로 활용되지 않는다. **결재가 필요한 핵심 결정은 세 가지다:**

1. Stage 3를 LightGBM으로 갈 것인가, 아니면 Bayesian 업데이트로 대체할 것인가
2. 피지수 AI 검토 레이어를 언제 삽입할 것인가 (UI placeholder 우선 vs 실제 연동 우선)
3. GanttTask → ZonePrediction 방향(공정표가 힌트를 준다)으로 할 것인가, 역방향(예측이 공정표를 업데이트)으로 갈 것인가

---

## 1. 현재 구현 정직한 진단

### Stage 1 — 타설 앵커 기반 (실제 동작, 일부 한계)

**동작 여부**: 동작한다.

**원리**: `DashboardStore`에 저장된 `concrete_data`(타설현황)를 읽어 `status === 'actual'`인 실적 타설만 앵커로 사용한다. 형틀/알폼/갱폼 팀의 `DailyWorkLog` 중 `dong`이 NULL인 레코드를 대상으로, 타설일 기준 D-7평일 ~ D-1평일 범위 내에 있으면 해당 동/층을 예측한다.

**실제 한계**:
- 신뢰도가 고정값 `0.92`다. 후보 단일 여부만 보고, 타설 사이클 8일 가정이 항상 맞지 않는다.
- 타설 데이터가 구형 형식이면 `isAlreadyMigrated()` 체크 실패 → 빈 맵 반환 → Stage 1 전체 무력화.
- 후보 복수(ambiguous) 케이스는 Stage 2로 넘기지만 Stage 2에서 이 정보를 활용하지 않는다.
- 타설 당일(D-0) 작업은 허용 안 함 → 타설팀 자신의 레코드 예측 불가(정상 설계이나 명시 필요).

### Stage 2 — 인접 레코드 보간 (실제 동작, 신뢰도 주관적)

**동작 여부**: 동작한다.

**원리**: 같은 팀의 날짜 시퀀스에서 이미 확인된 `dong`을 앵커로 삼아, NULL 레코드를 앞/뒤 앵커 기반으로 보간한다. 타설 앵커와 교차 검증 시 +0.05 보너스.

**실제 한계**:
- 신뢰도 계산이 주관적 고정값(양쪽 0.85, 한쪽 0.65, 전환 0.60)이다.
- 층(floor) 보간이 없다. 동(dong)만 추정되고 층은 인접 레코드의 층을 그대로 가져온다. 실제로 층이 달라질 수 있다.
- 공정표(GanttTask)와 연동이 전무하다.
- `byTeam` 그룹화 시 날짜순 정렬 후 순방향 보간을 하나, 이미 보간된 레코드를 `resolved` 배열에 반영하는 방식이라 역방향 전파가 없다.

### Stage 3 — LightGBM (미구현)

**동작 여부**: 미구현. `stage` 컬럼에 `3`이 예약되어 있고 라우트도 없다.

관리자가 확정(`confirmedAt` 기록)한 레코드가 쌓이고 있으나 Stage 3 학습 데이터로 활용되지 않는다.

### 관리자 확정 데이터 축적 현황

`confirm` API는 정상 동작한다. `stage=0, confidence=1.0, reason='수동확정'`으로 ZonePrediction에 기록된다. **누적 중이나 피드백 루프 없음**이 현 상태다.

---

## 2. 신뢰성·활용가치 향상 방안

### 2-1. 누적 학습 구조 — Stage 3 LightGBM 현실화 경로

LightGBM 파이썬 서버를 즉시 올리는 것은 과잉 투자다. 현실적 경로는 다음 3단계다.

**1단계 (지금 가능): 확정 데이터 품질 지표화**

```sql
-- 확정 레코드 중 Stage 1 예측과 일치율 계산
SELECT
  zp.stage,
  COUNT(*) AS total,
  SUM(CASE WHEN zp.dong = confirmed.dong THEN 1 ELSE 0 END) AS correct
FROM ZonePrediction zp
JOIN (SELECT logId, dong FROM ZonePrediction WHERE confirmedAt IS NOT NULL) confirmed
  ON zp.logId = confirmed.logId
GROUP BY zp.stage
```

이 쿼리만 돌려도 Stage 1/2 실제 정확도를 알 수 있다.

**2단계 (데이터 100건 이상 시): Bayesian 업데이트**

LightGBM 대신 더 단순하고 해석 가능한 방식 권장:

- 팀별·요일별·동별 과거 작업 빈도 테이블을 만든다 (`ZoneHistory` 뷰)
- 새 예측 시 "이 팀이 이 날짜에 이 동에서 일한 비율"을 사전확률로 사용
- Stage 1/2 rule-based 확률과 베이즈 결합

```
P(동|팀, 날짜) = P(Stage1 매칭) × P(역사 일치) / 정규화
```

신뢰도가 고정값에서 **데이터 기반 동적 값**으로 바뀐다.

**3단계 (500건 이상): LightGBM 또는 간단 로지스틱 회귀**

특징(feature):
- 팀명, 날짜(요일, 월), 인접 레코드의 동/층, 타설 앵커 거리(평일 수), 공정표상 예정 동/층

타겟: 관리자 확정 dong

이 단계에서야 Stage 3 API를 실제로 채운다.

### 2-2. 공정표 연동 강화

현재 `GanttTask` 테이블에는 `building`, `trade`, `startDate`, `endDate`, `content`가 있다. ZonePrediction은 이를 전혀 참조하지 않는다.

**연동 방향**: 공정표가 힌트를 준다 (GanttTask → ZonePrediction).

```typescript
// Stage 2 보강: 해당 날짜에 팀(trade)의 공정표가 가리키는 building이 있으면 우선 반영
const ganttHint = await db
  .select({ building: ganttTasks.building })
  .from(ganttTasks)
  .where(
    and(
      eq(ganttTasks.trade, normalizeTeamName(teamName)),
      lte(ganttTasks.startDate, log.date),
      gte(ganttTasks.endDate, log.date)
    )
  );
if (ganttHint.length === 1) {
  confidence += 0.08;  // 공정표 일치 보너스
  reason += ` +공정표확인(${ganttHint[0].building})`;
}
```

역방향(예측 → 공정표 업데이트)은 공정표의 신뢰성을 훼손할 수 있어 **관리자 수동 확정 후에만 선택적으로** 허용한다.

### 2-3. 타설 제약 자동화 개선

현재 `concrete_data`는 `DashboardStore`에 JSON 통째로 저장되며, 구형 형식이면 Stage 1이 통째로 무력화된다. 개선 방향:

- `ConcretePouringStatus` 전용 테이블을 만들어 JSON blob 의존을 제거한다
- `isAlreadyMigrated()` 실패 시 에러를 로그에 명시하고 fallback 동작을 정의한다
- 타설 실적 입력 즉시 Stage 1을 자동 재실행하는 webhook 구조를 추가한다

### 2-4. 신뢰도 점수 고도화

현재: stage별 고정값 (0.92, 0.85, 0.65, 0.60)

개선 후 신뢰도 산식:

```
confidence = base(stage) × 역사_보정(팀, 동) × 공정표_보정 × 타설_앵커_보정
```

| 인자 | 값 범위 | 설명 |
|------|---------|------|
| base(Stage1) | 0.88 | 단일 앵커 매칭 기본값 하향 조정 (0.92는 과신) |
| base(Stage2 양쪽) | 0.82 | 현행 0.85에서 소폭 하향 |
| 역사 보정 | 0.9 ~ 1.1 | 과거 동일 패턴 빈도 |
| 공정표 보정 | 1.0 ~ 1.1 | GanttTask 일치 시 +10% |
| 앵커 거리 보정 | 0.95 ~ 1.0 | D-1평일이면 1.0, D-7평일이면 0.95 |

### 2-5. 구간 이력 활용

새 뷰 `ZoneHistory` 추가:

```sql
-- 팀별·동별 작업 빈도 집계 (확정 데이터 기준)
CREATE VIEW ZoneHistory AS
SELECT
  dwl.teamName,
  zp.dong,
  strftime('%m', dwl.date) AS month,
  strftime('%w', dwl.date) AS dayOfWeek,
  COUNT(*) AS frequency
FROM DailyWorkLog dwl
JOIN ZonePrediction zp ON zp.logId = dwl.id
WHERE zp.confirmedAt IS NOT NULL
GROUP BY dwl.teamName, zp.dong, month,

... (잘림 — 원본: `/home/nas/H2OWIND_2/docs/ZONE_PREDICTION_BLUEPRINT.md`)

## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]
