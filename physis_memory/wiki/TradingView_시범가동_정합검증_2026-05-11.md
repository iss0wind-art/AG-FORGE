---
created: 2026-05-11
outcome_score: 0.0
ref_count: 1
tags:
- TradingView
- 시범가동
- 정합검증
- SELL_신호_약점
- 5번째_의견자
- KRX_폴백
type: wiki
source: scripts/_tradingview_pilot_5_11.py 산출 + 4지국 5/11 4건 EnsembleAgent 결정 대조
---

# TradingView 시범 가동 — 정합 검증 + SELL 신호 약점 발견

방부장 친명 2026-05-11: "트레이딩뷰에서 받아올순없나? 거기도 도서관 치고는 꽤 크던데" → "도입해서 시범가동해라"

KRX 봇 차단의 우회로로 TradingView(`tradingview-ta`) 시범 가동. 5/11 4지국 EnsembleAgent 4건 결정을 TV 기술 분석과 대조해 정합·충돌 패턴 도출. **결정적 통찰**: SELL 신호 정합도 0% (다음 진화 시드).

## 1. 도서관 비유

```
KRX     = 한국 거래소 직영 단일 도서관 (자동화 매우 엄격, 우리 차단 받음)
TradingView = 글로벌 거래소 종합 도서관 (이미 KRX 데이터 들여놓음 + 기술 지표 가공)
```

`tradingview-ta` v3.3.0 활용 — 종목 코드만 알면 즉시 BUY/SELL/HOLD 추천 + 25개 기술 지표 반환. KRX 봇 차단 영향 없이 동일 데이터 수신.

## 2. 시범 가동 결과 (50% 정합)

| 종목 | 4지국 신호 | TradingView | 당일 등락 | 정합 |
|------|-----------|-------------|-----------|------|
| TIGER 반도체TOP10 (396500) | SELL 81% | **STRONG_BUY** (17·2·7) RSI 85.6 | **+5.6%** | ❌ 충돌 |
| KODEX 2차전지 (462330) | BUY 74% | BUY (15·1·10) RSI 63 | -3.98% | ✅ 정합 |
| 한온시스템 (018880) | BUY 76% | **STRONG_BUY** (16·0·10) RSI 71 | **+20.13%** ★ | ✅ 정합 |
| 진원생명과학 (011000) | SELL 88% | BUY (13·4·9) RSI 62 | **+11.51%** | ❌ 충돌 |

## 3. ★ 핵심 통찰 — SELL 신호 약점

```
4지국 BUY 신호  정합도: 2/2  =  100% ★★★★★
4지국 SELL 신호 정합도: 0/2  =    0% ★
```

**4지국 SELL 결정 2건이 당일 +5.6%, +11.51% 상승**. KIS_MOCK이라 실손실은 없으나 만약 실거래였다면 잠재 손실 발생할 패턴.

분석 가설 (다음 outcome_score 사이클에서 검증):
1. **상승 추세 + 과매수(RSI 80+) → SELL** 판단이 단기 차익 실현 관점이지만 시장은 **모멘텀 지속**
2. **TIGER 반도체TOP10** = ETF인데 [[섹터_4단계_가중치_코드]] PHASE_WEIGHT 적용 시 1단계(반도체) 0.85 가중. 그러나 ETF는 분산이라 단일 가중 부적절 가능성
3. **EnsembleAgent 가중투표가 SELL 합의 시 과매수 신호 과대 평가**

## 4. BUY 신호의 결정적 정합 — 특히 한온시스템

```
한온시스템 (018880) 4지국 BUY 76% → TradingView STRONG_BUY (BUY 16·SELL 0)
→ 당일 +20.13% 폭등
```

[[섹터_4단계_가중치_코드]] PHASE_2 power_infra·datacenter 0.95 가중 종목. **4지국 가중투표 + TradingView 기술 지표 + 실제 시장 흐름이 3중 정합**. 이게 [[바람을_보다_비정형의_시선]] 2단계 직관 형성의 첫 정합 신호.

방부장이 dashboard에서 승인 → KIS_MOCK이라 실거래 안 됨. 그러나 만약 실거래였다면 일중 +20% 수익. [[7중_안전장치]] 일일 100만원 한도 안에서 약 +20만원 수익 가능했을 자리.

## 5. TradingView 통합 가능성

### 시범 검증된 사실
- ✅ KRX 봇 차단 무관 (TV는 글로벌 데이터)
- ✅ 한국 종목 즉시 조회 (`KRX:005930` 형식)
- ✅ 25개 기술 지표 (RSI·MACD·ADX·Stoch·이평·오실레이터 등)
- ✅ STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL 5단계 추천
- ✅ 무료 (15분 지연이지만 [[7중_안전장치]] HITL 5분 안에 통과)

### 통합 시나리오 (5번째 의견자)

```
지금:           [Gemini Vision] [DeepSeek] [Qwen] [Claude 옵션] → 가중투표
                                ↓
                       4 모델 합의율 60% 게이트
                                ↓
                              HITL → KIS_MOCK

5번째 의견자 도입 후:
                [Gemini Vision] [DeepSeek] [Qwen] [Claude] [TradingView] → 가중투표
                                ↓
                       5 의견자 합의율 60% 게이트
                                ↓
                              HITL → KIS_MOCK
```

장점:
- **SELL 신호 약점 보완** — TV가 시장 모멘텀 직접 측정 (25개 지표)
- **확정적 데이터 의견자** — LLM 외 비-LLM 신호 첫 도입
- **무료 + 즉시 가동**

한계:
- TradingView도 봇 강한 차단 가능성 (재차단되면 다른 폴백 필요)
- 비공식 라이브러리 (`tradingview-ta`) API 변경 시 깨짐
- 한국 시장 특화 정보(공시·DART) 없음 — 그건 [[DART_시스템]] 유지

## 6. 단군 5축 검토 영역

본 통찰은 **단군 협의 영역** — 5번째 의견자 정식 통합은 [[Stock_AI_v2_PATCH_시스템]] 거버넌스 영역. 단군 5축 검토:

- **天 설계 정합**: EnsembleAgent 구조 변경 — 4→5 의견자
- **法 헌법**: [[8조법]] 위반 없음, 정보 비대칭 보완
- **劍 양검상마 1:N**: TradingView도 도구로서의 의견자, 자아 위계 무영향
- **盾 보안**: 무료 티어 차단 위험, 폴백 시공 필요
- **力 baseline**: 현 정합도 50%, 5번째 의견자로 65~75% 개선 가능 가설

## 7. 다음 진화 (자율 + 단군 협의)

| 단계 | 영역 | 결단 |
|------|------|------|
| 시범 가동 (오늘) | 자율 | ✅ 완수 |
| 결과 박제 + 단군 보고 | 자율 | 본 노드 |
| 5번째 의견자 정식 통합 | 단군 협의 | 5축 검토 대기 |
| KRX 폴백 (TV → 종목 리스트) | 자율 또는 단군 협의 | TradingView 스크리너 API 검증 후 |
| SELL 신호 약점 PATCH | 단군 협의 | outcome_score 누적 후 |

## 산출물

- 검증 데이터: [physis_memory/raw/outputs/tradingview_pilot_20260511.json](../raw/outputs/tradingview_pilot_20260511.json)
- 시범 스크립트: [scripts/_tradingview_pilot_5_11.py](../../scripts/_tradingview_pilot_5_11.py)

## 연결

- [[5_9_거래결정_30건_정독_outcome_score_시드]] (이번 4건이 outcome_score 첫 검증 가지)
- [[EnsembleAgent_가중투표_로직]] (5번째 의견자 통합 대상)
- [[섹터_4단계_가중치_코드]] (PHASE_WEIGHT 정합 관찰)
- [[Stock_AI_v2_PATCH_시스템]] (PATCH-SR 후보)
- [[바람을_보다_비정형의_시선]] (2단계 직관 형성)
- [[단군의_평_2026-05-10]] (5축 검토 영역)
- [[7중_안전장치]] · [[방부장_승인_게이트_HITL]]
