---
type: wiki
created: 2026-05-09
tags: [h2owind, 2지국, zone-prediction, stage1.5, physis-interface, ai-protocol]
ref_count: 0
outcome_score: 0.0
---

# H2OWIND_zone-prediction_stage1.5_ai_interface

# Stage 1.5 — 피지수가 받게 될 호출 인터페이스 명세

[[H2OWIND_zone-prediction_stage1.5_implementation]]의 1순위 응답자가 피지수다. 이 노트는 피지수 자신이 자기에게 들어오는 task 형식과 기대 응답을 알고 있도록 학습시키는 자기참조 명세.

## 호출 경로

`lib/ai/zonePredictionAI.ts::resolveAmbiguous()` → `askPhysis(task)` (`lib/ai/physisClient.ts`).

`PhysisResponse.constitution_passed === true` AND `JSON.parse(response)` 성공이어야 채택. 둘 중 하나라도 실패하면 자동으로 Gemini 1.5 Flash 폴백.

## task 입력 형식 (그대로)

```
[Stage 1.5 ambiguous 해소 요청 — 형틀/알폼/갱폼 팀 작업로그가 어느 동·층을 향하는가]

작업일: YYYY-MM-DD
팀명: 형틀1팀 (등)
작업 원문: <dailyWorkLog.content 원문, 없으면 "(원문 없음)">

후보 (모두 작업일 기준 D-7~D-1 평일 안에 들어오는 타설 앵커):
  1. 101동 5층 (타설일 2026-05-15, 소스 pour)
  2. 102동 5층 (타설일 2026-05-16, 소스 gantt)
  ...

판단 규칙:
- 작업 원문에 동(예: "101동", "201동") 또는 층(예: "5층", "B1") 언급이 있으면 그 후보를 우선
- 같은 팀이 며칠 연속 같은 동을 작업하는 패턴이 자연스러움
- 원문에 단서가 전혀 없으면 confidenceLevel='Low'
- 후보 중 정확히 하나만 합리적이면 'High', 둘 이상이 그럴듯하면 'Medium'

응답 JSON:
{ "chosenDong": "...", "chosenFloor": "...", "confidenceLevel": "High|Medium|Low", "reason": "한 문장 근거" }
```

## 응답 스키마 (필수)

```json
{
  "chosenDong": "101동",
  "chosenFloor": "5층",
  "confidenceLevel": "High",
  "reason": "원문에 '101동 기둥 형틀'이 명시되어 있음"
}
```

- `chosenDong`/`chosenFloor`는 **후보 목록에 실제 존재하는 조합**이어야 함. 환각 시 호출 측이 폐기.
- `confidenceLevel`은 enum 3종만: `"High"` (0.78), `"Medium"` (0.68), `"Low"` (0.55).
- `reason`은 **한 문장 한국어**.

## 잘 답하는 패턴

- 작업 원문에 "101동", "5층", "B1" 같은 직접 언급이 있을 때 → High
- 원문이 비어있어도, 후보가 "101동 5층 D-2"와 "201동 5층 D-7"처럼 시간 거리가 다르면 가까운 쪽이 우선 → Medium
- 같은 팀의 인접 일자(작업일 ±3일)에 특정 동이 자주 등장하면 Medium 보너스

## 회피해야 할 패턴

- 후보에 없는 동/층을 만들어내기 (환각). 호출 측 검증에서 폐기됨.
- 모든 응답을 High로 답하기. cap=0.78이라도 Stage 2의 "양쪽 앵커 일치"(0.85)보다 낮음을 인지.
- "확실하지 않다" 같은 자연어 회피. enum 어기면 Gemini 폴백으로 떨어짐.

## 헌법 통과 조건

`PhysisResponse.constitution_passed`가 false면 호출 측이 즉시 Gemini로 우회. 즉, 8조 금법(특히 #7 폭주 경계, #5 오류 포용)과 정합한 응답이어야 채택됨.


## 연결

- [[홍익인간]]
