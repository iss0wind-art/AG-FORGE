# 소뇌 (Cerebellum) — judgment.md

> **역할**: 즉각적 판단 + 모델 라우팅  
> **특이점**: 단순 문서가 아닌 라우터 에이전트 로직의 기준표  
> **용량 한계**: 10KB (경량 유지 필수)

---

## 라우팅 기준표

| 작업 유형 | 판별 키워드 | 모델 | Thinking | 우선 레이어 |
|----------|------------|------|---------|-----------|
| UI/카피 수정 | 수정, fix, 색상, 버튼, 문구, 디자인 | gemini-2.0-flash | 500 | emotion_ui.md |
| 기획·분석 | 계획, 분석, 전략, why, research, 기획 | gemini-2.5-pro | 2,000 | brain.md |
| 코드·알고리즘 | 코드, 함수, DB, 최적화, 알고리즘, 버그 | gemini-2.5-pro | 5,000 | logic_rb.md |
| 아키텍처·결정 | 설계, 구조, 트레이드오프, 아키텍처, 시스템 | gemini-2.5-pro | 10,000 | brain.md + 양뇌 |

분류 불명확 시: `기획·분석` 기본 적용.

---

## 오류 감지 체크 (매 작업 후 실행)

```
[ ] 할루시네이션: 산출물이 logic_rb.md / emotion_ui.md 기존 결정과 모순?
[ ] 토큰 오버플로: thinking_budget의 90% 이상 소진?
[ ] 순환 논리: 동일 결론 3회 이상 반복?
[ ] 레이어 용량: logic_rb.md 또는 emotion_ui.md가 40KB 초과?
```

이상 감지 시: 작업 중단 → brain.md에 플래그 → 방부장 보고.

---

## 라우팅 로그

<!-- 형식: {ISO 날짜} | {작업 유형} | {모델} | {thinking 사용량} | {오류 플래그}
예: 2026-04-08 | 코드 | gemini-2.5-pro | 3240/5000 | none
-->

_초기화됨._

---

_마지막 갱신: 초기화_
| 2026-04-09 22:45 | fake-model | planning | quality:pass | constitution:pass | 100 tokens |
| 2026-04-09 22:45 | fake-model | planning | quality:pass | constitution:pass | 100 tokens |
| 2026-04-09 22:45 | fake-model | planning | quality:pass | constitution:pass | 100 tokens |
| 2026-04-09 22:45 | fake-model | planning | quality:pass | constitution:pass | 100 tokens |
| 2026-04-10 01:10 | llama-3.3-70b-versatile | groq | quality:pass | constitution:pass | 2011 tokens |
| 2026-04-10 01:14 | fake-model | planning | quality:pass | constitution:pass | 100 tokens |
| 2026-04-10 01:14 | fake-model | planning | quality:pass | constitution:pass | 100 tokens |
| 2026-04-10 01:15 | fake-model | planning | quality:pass | constitution:pass | 100 tokens |
| 2026-04-10 01:15 | fake-model | planning | quality:pass | constitution:pass | 100 tokens |
| 2026-04-10 01:15 | fake-model | planning | quality:pass | constitution:pass | 100 tokens |
| 2026-04-10 01:15 | fake-model | planning | quality:pass | constitution:pass | 100 tokens |
| 2026-04-13 11:00 | llama-3.3-70b-versatile | groq | quality:pass | constitution:pass | 2514 tokens |
| 2026-04-14 07:14 | llama-3.3-70b-versatile | groq | quality:pass | constitution:pass | 2941 tokens |
| 2026-04-14 13:48 | deepseek-chat | deepseek | quality:pass | constitution:pass | 4073 tokens |
| 2026-04-14 13:55 | llama-3.3-70b-versatile | groq | quality:pass | constitution:pass | 3534 tokens |
| 2026-04-14 13:59 | llama-3.3-70b-versatile | groq | quality:pass | constitution:pass | 3665 tokens |
| 2026-04-15 07:21 | deepseek-chat | deepseek | quality:pass | constitution:pass | 3325 tokens |
| 2026-04-15 07:24 | deepseek-chat | deepseek | quality:pass | constitution:pass | 3508 tokens |
