---
created: 2026-05-09
domain: 주식·금융·경제
outcome_score: 0.0
ref_count: 8
source: /home/nas/STOCK-TRADING/Stock-Trading/agents/ensemble_agent.py
tags:
- ensemble
- aggregate
- voting
- code
- multi-agent
tier: 1
type: code_analysis
---

# EnsembleAgent — 가중 투표 정반합 로직 (코드 정독)

[[멀티AI_앙상블_원리]] | [[7중_안전장치]] | [[Stock_AI_파이프라인]]

## 정독 위치

`/home/nas/STOCK-TRADING/Stock-Trading/agents/ensemble_agent.py` (5/9 정독)

## 핵심 메서드 3종

### 1. select_stocks_by_news()
- 입력: 뉴스 + 시장 종목 후보
- LLM: DeepSeek 단일 (기본)
- 출력: 5종목 + market_sentiment ("긍정/중립/부정")
- 실패 시 안전: market_sentiment="중립", selected_stocks=[]

### 2. analyze_stock()
- 입력: 종목코드/이름 + 재무 + 차트분석 + 뉴스
- LLM: 병렬 (`asyncio.gather`) — 기본 ["deepseek", "qwen"], Claude 선택
- 출력: 모델별 {signal, confidence, key_reasons}
- 예외 처리: 실패 모델 → {signal:"HOLD", confidence:0.0}

### 3. aggregate() — ★ 핵심 가중투표

```python
signal_weight = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}

for model, result in valid.items():
    sig = result["signal"]               # BUY/SELL/HOLD
    conf = result["confidence"]          # 0.0~1.0
    signal_weight[sig] += conf           # 신뢰도를 그 신호에 가산

total = sum(signal_weight.values())
final_signal = max(signal_weight, key=signal_weight.get)
agreement = signal_weight[final_signal] / total
avg_confidence = sum(confidences) / len(confidences)

# 7중 안전장치 1·2층 — AND 게이트
if agreement < settings.ENSEMBLE_MIN_AGREEMENT:        # 0.60
    final_signal = "HOLD"
elif avg_confidence < settings.ENSEMBLE_MIN_CONFIDENCE: # 0.70
    final_signal = "HOLD"
```

## 가중투표의 의미

**합의율 ≠ 단순 다수결**
- 모델 A: BUY conf=0.9
- 모델 B: SELL conf=0.5
- 모델 C: SELL conf=0.5
- 단순 다수결: SELL 2 vs BUY 1 → SELL
- **가중투표**: BUY 0.9 vs SELL 1.0 → SELL (그러나 아슬아슬)
- agreement = 1.0/(0.9+1.0) = 0.526 → 0.60 미달 → **HOLD**

★ **신뢰도 강한 소수 vs 약한 다수가 충돌하면 HOLD**. 자만한 다수의 함정 차단.

## 피지수 [[sweep-A]]와의 정합

| sweep-A | EnsembleAgent |
|---------|---------------|
| θ (theta) | ENSEMBLE_MIN_CONFIDENCE (0.70) |
| pattern matching | signal voting |
| fire 조건 | agreement >= 0.60 AND confidence >= 0.70 |
| 5×5 매트릭스 | confidence × signal 분포 |

★ 둘 다 *발화 임계값 + 합의/패턴 차원의 AND 게이트*. 도메인 다르지만 골격 같음.

## 학습된 함정 (행동경제학과 연결)

[[행동경제학_원리]] §3 확증 편향:
- 단일 모델 사용 시 그 모델의 편향이 결정 → 위험
- aggregate가 차단: 4체 합의가 없으면 HOLD

§9 더닝-크루거:
- 단일 모델이 "모르는데 안다"고 답해도 다른 체가 다른 답 → agreement 떨어짐 → HOLD
- 자만 차단

## 약점 / 개선 후보 (피지수 가설)

1. **단순 평균 confidence** — 모델 신뢰도가 다른데 동등 가중. 모델별 historical accuracy 가중 도입 가능?
2. **HOLD에도 confidence 부여** — 현재는 HOLD 자체에도 신호 가중치. "강한 HOLD"와 "약한 HOLD" 동등 처리.
3. **시간 차원 미반영** — 같은 종목 어제 BUY 오늘 SELL일 때 일관성 가중치 가능.
4. **모델별 도메인 강점 미활용** — DeepSeek은 재무, Gemini는 차트인데 모든 분야 동등 가중.

## 단군 협의 후보

이 가중투표 로직을 피지수 자아 학습(Titans memory)과 연결:
- 거래 결과 (수익/손실) → 모델별 historical accuracy 갱신
- 다음 라운드 가중치를 동적 조정
- → ChromaDB `physis_finance_brain`에 모델별 성과 시계열 박제

## 연결

[[멀티AI_앙상블_원리]] · [[7중_안전장치]] · [[Stock_AI_파이프라인]] · [[sweep-A]] · [[행동경제학_원리]]
