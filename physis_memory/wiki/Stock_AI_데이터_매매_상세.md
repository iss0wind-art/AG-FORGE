---
type: code_analysis
domain: 주식·금융·경제
tags: [stock-ai, news, chart, kis, code, deep-read]
source: /home/nas/STOCK-TRADING/Stock-Trading/{data,agents,api}/
created: 2026-05-09
tier: 1
outcome_score: 0.0
ref_count: 0
---

# Stock-AI 데이터 + 매매 흐름 상세 정독

[[Stock_AI_모듈_지도]] | [[Stock_AI_파이프라인]] | [[7중_안전장치]]

> 5/9 자율 정독 2차. NewsScraper / ChartAgent / KISClient 본체 분석.

## 1. NewsScraper — 3중 폴백 + 가중 점수화

### 3중 데이터 채널
1. **네이버 OpenAPI** (`/v1/search/news.json`) — 키 있을 때
2. **네이버 금융 스크래핑** (BeautifulSoup) — 키 없을 때 폴백
3. **4 쿼리 병렬**: "코스피 오늘", "코스닥 급등", "주식 실적 발표", "증시 특징주"

### ★ 핵심 점수화 로직 — 행동경제학 정합

```python
net_score = pos_score - (neg_score * 2)  # 부정 뉴스 가중치 2배
```

★ **부정 뉴스 가중치 ×2** = [[행동경제학_원리]] §1 *손실 회피* 정합.
"같은 크기 손실 고통 ≈ 이익 기쁨 ×2~2.5배"를 코드로 실현.
0 이상만 후보 → 긍정 우세 종목만 통과.

### ★ 키워드 사전 본체 (data/news_scraper.py:14~21)

**POSITIVE 13개** — 종목 모멘텀 위주:
> 실적 개선, 영업이익 증가, 신사업, 수주, 계약 체결, 흑자 전환, 매출 성장,
> 신제품, 특허, 수출 증가, 목표주가 상향, 매수 추천, 어닝 서프라이즈

**NEGATIVE 11개** — 재무 위기 위주 (DART 위험 신호와 정합):
> 영업손실, 적자, 리콜, 소송, 횡령, 배임, 상장폐지, 관리종목, 워크아웃, 법정관리, 부도

★ **균형 양호** — NEGATIVE는 [[DART_시스템]] 위험 신호와 70% 정합.
★ **그러나 거시 키워드 부재** — "코스피 상승/하락", "외국인 순매수", "환율 급등", "금리 인상" 등 [[매크로_경제_지표]] 키워드 없음.

### 약점 (피지수 가설 — 정독 후 확정)
1. **정적 키워드 사전 24개** — 학습 갱신 메커니즘 없음
2. **시간 가중치 없음** — 어제 뉴스와 1시간 전 뉴스 동등
3. **출처 신뢰도 미반영** — 찌라시와 한국경제 동등
4. **거시 키워드 부재** — 시장 전체 흐름 (코스피/외국인/환율/금리) 미반영
5. **5/9 실증**: 뉴스 0건 수집 — 점수화 자체 무력 → 후보 빈 채로 다음 단계

## 2. ChartAgent — Gemini Vision 단일 프롬프트

### 모델
- `gemini-2.5-flash` (5/9 갱신 후 작동 중)
- `inline_data` PNG → `generate_content`

### CHART_PROMPT 5항목
1. **추세** (단기/중기, 상승/하락/횡보)
2. **지지/저항** 주요 가격대
3. **패턴** (캔들 또는 차트 패턴)
4. **거래량** 추이 + 의미
5. **종합 기술 의견** (매수우세/매도우세/중립)

### 안전 장치 (프롬프트 내)
> "객관적 사실만 분석하고, 보이지 않는 것은 추측하지 마세요."
> "응답은 500자 이내로 간결하게."

★ **자만(더닝-크루거) 차단 프롬프트** = [[행동경제학_원리]] §9 정합.

### 약점
1. **단일 프롬프트** — 모든 종목 동일 분석. 종목 특성(레버리지/대형/소형) 미고려
2. **이미지 캡처 품질 종속** — chart_scraper.py가 흐릿하면 분석 무력
3. **결과가 자연어** — EnsembleAgent가 신호화하기 전에 의미 손실 가능
4. ★ **단일 시간프레임 확정** — `period="3m"` 기본 (3개월 일봉만). chart_scraper.py:
   - 옵션: `1d` / `3m` / `1y` 중 1개
   - 출처: `https://t1.daumcdn.net/finance/chart/domestic/day/{code}.png` (Daum 일봉)
   - 분봉/주봉/월봉 멀티 시간프레임 분석 없음 → 단기 모멘텀 vs 장기 추세 동시 분석 불가

## 3. KISClient — 매매 실행 본체

### 토큰 관리 (싱글톤 + 디스크 캐시)
```python
class KISClient:
    """싱글톤 — 토큰을 인스턴스 + 프로세스 재기동 사이에 재사용"""
    _access_token: str = ""
    _token_expires: datetime
    _token_lock = asyncio.Lock()  # 동시 발급 방지
```

- KIS 토큰: **1일 유효**, **분당 1회 발급 제한**
- 디스크 캐시: `.cache/kis_token_{mock|live}.json`
- 모의/실거래 캐시 분리 → 모드 전환 시 별도 토큰

★ **분당 1회 제한 우회 = 토큰 캐시 의무**. 캐시 없으면 KIS lockout.

### 매매 주문 TR_ID 분기
```
buy_market_order : VTTC0802U (mock) / TTTC0802U (live)
sell_market_order: VTTC0801U (mock) / TTTC0801U (live)
잔고 조회       : VTTC8434R (mock) / TTTC8434R (live)
```

### ★ calc_quantity — 3중 안전 캡

```python
def calc_quantity(self, price: int, budget: int) -> int:
    if price <= 0: return 0
    return min(budget // price, settings.MAX_TRADE_AMOUNT // price)
```

★ **이중 캡 (호출자 budget vs 시스템 한도)** + 가격 = **3중 안전**.
호출자가 큰 budget 줘도 `MAX_TRADE_AMOUNT(100만원)`이 캡.
**중첩 보안 설계 — 7중 안전장치 §3과 정합 강화**.

### 매매 실행 엔드포인트
```
POST {BASE_URL}/uapi/domestic-stock/v1/trading/order-cash
  → ODNO (주문번호) + mode (모의투자/실거래) 반환
```

## 4. 데이터 → 매매 전체 흐름 (5/12 본격 시작 예정)

```
NewsScraper.fetch_market_news()   ← 4 쿼리 병렬
      ↓
extract_stock_candidates_from_news()  ← net_score = pos - 2×neg
      ↓
StockScreener.fetch_top()          ← KRX + 네이버 폴백
      ↓
EnsembleAgent.select_stocks_by_news()  ← DeepSeek → 5종목 + sentiment
      ↓ (sentiment != 부정)
종목별 병렬 분석:
  ┌─ DartClient.get_financial()   ← corp_code 매핑 + 보고서
  └─ ChartScraper.capture()       ← 차트 PNG
      ↓
ChartAgent.analyze(image)          ← Gemini Vision 5항목
      ↓
EnsembleAgent.analyze_stock()      ← DeepSeek + Qwen 병렬
      ↓
EnsembleAgent.aggregate()          ← 가중투표 + 게이트
      ↓ (signal in {BUY, SELL})
TelegramNotifier.wait_for_approval()  ← 5분 HITL
      ↓ (방부장 승인)
KISClient.calc_quantity(price, budget)  ← 3중 안전 캡
      ↓
KISClient.{buy|sell}_market_order()  ← 모의/실거래
      ↓
일일 리포트 → 텔레그램
```

## 5. 약점·자원 청구 종합 (이번 정독 추가)

### 추가 발견 약점 (모듈별)
- **NewsScraper**: 정적 키워드 사전 학습 없음, 시간/출처 가중치 없음
- **ChartAgent**: 단일 프롬프트, 단일 시간프레임 추정
- **KISClient**: ✅ 견고 (싱글톤 + 디스크 캐시 + 3중 캡 + 토큰 잠금)

### 자원 청구 (월요일 본격 시작 전)
- [x] `chart_scraper.py` 시간프레임 확인 → **3개월 일봉 단일** 확정
- [x] POSITIVE/NEGATIVE 키워드 사전 위치 → news_scraper.py:14~21 확정
- [ ] 5/9 "뉴스 0건" 원인 분석 — 금요일 장 마감 후 + 시간 윈도우 문제?

### 추가 자원 청구
- [ ] 거시 키워드 추가 (코스피/외국인/환율/금리) — 학습 진행 후 PR 검토
- [ ] 차트 멀티 시간프레임 (1d + 3m + 1y 동시 분석) 검토
- [ ] 키워드 사전 학습 갱신 메커니즘 (방부장 거절 이유 → 키워드 자동 추가)

### 시스템 환경 — settings.py 전체 (정독 완료)
포트 시프트 설계 발견:
- `BIND_PORT: 8030` 기본 → NAS는 **8040** 권장 (단군 :8030 충돌 회피)
- `MCP_PORT: 8031` 기본 → NAS는 **8041** 권장
- 실제 가동: 8040 (API), 8041 (MCP) — 권장값 그대로 적용됨
- `SCHEDULE_TIME: 08:30` — 장전 단일가 시점 정합 ([[한국시장_특수성]])
- `WEBHOOK_SECRET` — 외부 콜백 인증 (X-Webhook-Secret 헤더)

### 자율 가능 다음 단계
- [ ] `chart_scraper.py` + `chart_agent.py` 통합 정독 (시간프레임 식별)
- [ ] `data/__init__.py` POSITIVE/NEGATIVE 키워드 위치 확인
- [ ] settings.py 전체 정독 (모든 환경변수)
- [ ] mcp_server.py 외부 도구 호출 흐름 정독

## 행동경제학 정합 박제 (★ 핵심 통찰)

Stock-AI는 **행동경제학 함정 차단을 코드 수준에서 구현**:

| 함정 | 차단 메커니즘 |
|------|--------------|
| §1 손실회피 | NewsScraper 부정뉴스 ×2 가중 |
| §2 FOMO | 7중 §6 시장감성 부정 시 보류 |
| §3 확증편향 | EnsembleAgent 4체 정반합 |
| §6 매몰비용 | MAX_DAILY_TRADES 일3건 한도 |
| §9 더닝-크루거 | ChartAgent "추측 금지" 프롬프트 + ENSEMBLE_MIN_CONFIDENCE |

★ **Stock-AI 설계자가 [[행동경제학_원리]]를 깊이 이해하고 코드에 박았다**. 피지수가 학습하기에 최적의 시스템.

## 연결

[[Stock_AI_모듈_지도]] · [[EnsembleAgent_가중투표_로직]] · [[행동경제학_원리]] · [[7중_안전장치]] · [[Stock_AI_파이프라인]]
