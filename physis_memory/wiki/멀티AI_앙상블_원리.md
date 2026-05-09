---
type: ai_principle
domain: 주식·금융·경제
tags: [ensemble, multi-agent, llm, 정반합]
source: Stock-Trading/agents/ensemble_agent.py + chart_agent.py
created: 2026-05-09
outcome_score: 0.0
ref_count: 0
---

# 멀티 AI 앙상블 원리 — Stock AI 정반합

[[주식_금융_경제_도메인]] | [[Stock_AI_파이프라인]] | [[이천_大業_알고리즘_명세]]

## 4체 분담 (Stock AI)

| 체 | LLM | 강점 | 담당 |
|----|-----|------|------|
| 1체 | DeepSeek | 재무 수치 추론, 극저가 | 종목 선정 + 재무 분석 |
| 2체 | Gemini Vision | 무료, 이미지 분석 | 차트 이미지 기술적 분석 |
| 3체 | Qwen | 아시아 시장 맥락, Alibaba | 한국 시장 컨텍스트 |
| 4체 | Claude (선택) | 리스크 분석 | 위험 시나리오 + 보수적 판단 |

## 출력 메트릭

- **action**: BUY / SELL / HOLD
- **confidence**: 0.0 ~ 1.0 (개별 모델 신뢰도)
- **agreement**: 합의율 (4체 중 동일 action 비율)
- **rationale**: 자연어 추론 근거

## 게이트 통과 조건 (AND)

```
confidence_avg ≥ 0.70 AND agreement ≥ 0.60
```

7중 안전장치 1·2층. 둘 중 하나만 미달해도 자동 HOLD.

## 피지수 자기 매핑

이 구조는 [[이천_大業_알고리즘_명세]] 5체 정반합과 동일 골격:
- 이천: DeepSeek(기둥)+Gemini(보슬라브)+Groq(벽체)+Claude(기타)+DeepSeek(합)
- Stock AI: DeepSeek(재무)+Gemini(차트)+Qwen(시장)+Claude(리스크)

**도메인 다르지만 정반합 골격 같다.** 피지수의 "5체 정반합"이 이 둘에 동시 적용된다는 점이
사지(Jiim)·자아(Physis) 양립 구조의 실증.

## 학습 포인트

1. **각 LLM의 강점이 도메인별로 다르다** — 같은 모델이라도 적용 영역에 따라 신뢰도 분포 다름
2. **합의율은 다양성을 측정** — 4체 모두 BUY = 1.0 (강한 합의), 3 BUY 1 SELL = 0.75
3. **신뢰도와 합의율은 독립 차원** — 합의율 100%인데 신뢰도 50%일 수 있음 (모두 약한 신호)
4. **HITL은 5층 위에 얹는다** — AI 합의 위에 인간 결단

## 단군 권고 잠재 적용

`scripts/sweep_a.py` 5×5 매트릭스의 (θ, pattern) 조합 분석을 Stock AI 게이트 튜닝에 응용 가능:
- θ ≈ confidence threshold
- pattern ≈ agreement type (and_tokens / or_tokens 등)

→ 파라미터 자기조정 학습의 바탕.

## 연결

[[Stock_AI_파이프라인]] · [[7중_안전장치]] · [[이천_大業_알고리즘_명세]] · sweep_a
