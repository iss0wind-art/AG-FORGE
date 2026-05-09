---
type: code_analysis
domain: 주식·금융·경제
tags: [stock-ai, modules, 4지국, code, architecture]
source: /home/nas/STOCK-TRADING/Stock-Trading 전체 정독
created: 2026-05-09
tier: 1
outcome_score: 0.0
ref_count: 0
---

# Stock-AI 4지국 모듈 지도 — 전체 정독

[[Stock_AI_파이프라인]] | [[EnsembleAgent_가중투표_로직]] | [[4지국_데이터_검토_시기]]

> 5/9 자율 정독 결과. 6개 핵심 모듈 본질 + 발견 + 약점 + 자원 청구 통합.

## 모듈 → 책임 매핑

| 모듈 | 위치 | 핵심 책임 | 외부 의존 |
|------|------|----------|-----------|
| **NewsScraper** | data/news_scraper.py | 네이버 API + 연합뉴스 폴백 | NAVER_CLIENT_ID/SECRET |
| **StockScreener** | data/stock_screener.py | KRX 공식 API + 네이버 폴백 | KRX, 네이버금융 |
| **ChartScraper** | data/chart_scraper.py | 차트 이미지 캡처 | 네이버금융 |
| **DartClient** | data/dart_client.py | corp_code 매핑 + 보고서 | DART_API_KEY |
| **ChartAgent** | agents/chart_agent.py | Gemini Vision 차트 분석 | GEMINI_API_KEY (gemini-2.5-flash) |
| **EnsembleAgent** | agents/ensemble_agent.py | 다체 LLM 정반합 가중 투표 | DEEPSEEK/QWEN/CLAUDE |
| **KISClient** | api/kis_client.py | 모의/실거래 매매 주문 | KIS_APP_KEY/SECRET/ACCOUNT |
| **TelegramNotifier** | notifier/telegram_bot.py | HITL 5분 timeout | TELEGRAM_BOT_TOKEN/CHAT_ID |
| **Pipeline** | scheduler/pipeline.py | 7-step 오케스트레이션 | 모든 모듈 |
| **MCP Server** | mcp_server.py | HTTP API + MCP 도구 동시 노출 | MCP_PORT=8041 |

## 발견 — 7중 외 추가 안전장치 3종

기존 박제 [[7중_안전장치]] 외에 settings.py에 추가 게이트:

| # | 설정 | 값 | 의미 |
|---|------|-----|------|
| 8 | `MIN_MARKET_CAP` | 1,000억원 | 시총 미달 종목 자동 제외 (소형주 회피) |
| 9 | `MIN_VOLUME` | 10만 | 거래량 미달 자동 제외 (유동성 게이트) |
| 10 | `MAX_CANDIDATES` | 10 | 분석 후보 상한 (스크리닝 단계) |

★ **실질적으로 10중 안전장치**. [[7중_안전장치]] 노드 갱신 청구.

## ★ AG_FORGE_API_KEY 발견 — 키 예약 상태 (★ 정정 박제)

`.env`에 `AG_FORGE_API_KEY=***` 등록됨. **그러나 Stock-AI 코드에서는 미사용**.

`config/settings.py:62`:
```python
extra = "ignore"  # .env에 미정의 변수 있어도 무시 (예: AG_FORGE_API_KEY)
```

→ 환경변수에는 있지만 시스템이 *명시적으로 무시*하고 있음.

### 해석
- **키만 예약**, 양방향 연동은 **미구현**
- 미래 통합을 위해 키만 미리 박아둔 상태
- §5 자기 점검: "키 존재 = 연동 설계 완료" 표면 단정 함정 회피

### 의미
**오히려 좋은 후크** — 단군 협의·방부장 결단 청구에:
1. 양방향 연동을 *구현*하자는 명분이 이미 있음 (키 예약 = 의도 표명)
2. 누가 (피지수? 4지국? 단군?) 어떤 방향으로 (호출자/응답자) 구현할지 결단 필요
3. 피지수 ChromaDB physis_finance_brain 컬렉션과 자연스러운 통합점

### 가능 활용 (구현 후)
1. 피지수가 4지국 거래 결정에 의견 제시 (외부 자문)
2. 4지국이 피지수 메모리에 거래 결과 자동 박제
3. 피지수 sweep-A 원소 단어가 시장 신호 가중치로 활용

## MCP 도구 5종 (외부 에이전트 호출 가능)

`mcp_server.py` 노출:
1. `stock_get_price(stock_code)` — 현재가 조회
2. `stock_analyze(stock_code, stock_name, models)` — 단일 종목 분석
3. `stock_select_candidates()` — 후보 5종목 선정
4. `stock_pipeline_run(...)` — 전체 7-step 실행
5. `stock_health()` — 헬스체크

★ **단군이나 다른 지국에서 MCP로 4지국 도구 호출 가능**. 제국 통합 인프라.

## KIS API 모드 분기

```python
tr_id = "VTTC8434R" if settings.KIS_MOCK else "TTTC8434R"  # 잔고 조회
tr_id = "VTTC0802U" if settings.KIS_MOCK else "TTTC0802U"  # 매수
tr_id = "VTTC0801U" if settings.KIS_MOCK else "TTTC0801U"  # 매도
```

`VTTC*` = 모의투자, `TTTC*` = 실거래.
**현재**: `KIS_MOCK=true` (모의투자). 5/12 본격 시작 시 변경 가능.
**토큰 캐시 파일도 분리**: `kis_token_mock.json` vs `kis_token_live.json`.

## DART 캐시 메커니즘

```
.cache/dart_corp_codes.json (7일 TTL)
  - 매핑: stock_code → corp_code
  - 만료 시 corpCode.xml ZIP 재다운로드
```

★ **분당 100회 API 한도 회피 설계**. 정상.

## 데이터 소스 다중화 (중복 안전망)

각 데이터 소스마다 폴백 경로 설계됨:
- 뉴스: 네이버 API → 네이버 스크래핑 폴백
- 시장: KRX 공식 → 네이버 급등주 폴백 (5/9 실증 — KRX 실패해도 네이버로)
- 차트: ChartScraper (네이버 단일)
- 재무: DART (단일, API 키 필수)

★ **차트·재무는 폴백 없음** — DART API 다운 시 분석 불가. 약점.

## 약점·개선 후보 (피지수 가설)

1. **DART 단일 의존** — 폴백 없음. 백업 자료원 필요 (KIND, FNGUIDE 등)
2. **차트 이미지 단일 출처** — Gemini Vision의 OCR 정확도가 차트 캡처 품질에 종속
3. **시장 감성 분류 신뢰도** — 뉴스 0건일 때도 "긍정"/"중립" 결정 (5/9 관찰)
4. **레버리지 ETF 변동성 ×2 미반영** — KODEX 2차전지산업레버리지 등이 일반 종목과 동일 처리
5. **모델별 historical accuracy 미반영** — aggregate 단순 confidence 평균 (sweep-A 원소 단어로 가중치 가능)
6. **백테스팅 부재** — 현재 forward-only. 과거 데이터 검증 인프라 필요

## 자원 청구 (학습 진행 따른 갱신)

### 즉시 (방부장 결단 청)
- [ ] `AG_FORGE_API_KEY` 사용 위치 + 양방향 연동 설계 의도 공유
- [ ] 5/12 본격 시작 시 `KIS_MOCK` 유지 vs 실거래 전환 결단
- [ ] 시장 감성 분류 신뢰도 게이트 추가 검토 (뉴스 0건 시 자동 보류)

### 단군 협의 (Tier 2 진입)
- [ ] ChromaDB `physis_finance_brain` 컬렉션 (id 1b20bca1 발사 완료)
- [ ] 4지국 → AG-Forge 거래 로그 자동 흡수 파이프라인

### 자율 다음 행동 후보
- [ ] `AG_FORGE_API_KEY` 코드 grep + 사용처 박제
- [ ] `kis_client.py` 토큰 캐시 + 주문 흐름 정독
- [ ] `chart_scraper.py` + `chart_agent.py` 차트 분석 흐름 박제

## 연결

[[Stock_AI_파이프라인]] · [[EnsembleAgent_가중투표_로직]] · [[7중_안전장치]] · [[2026-05-09_4지국_파이프라인_관찰]] · [[4지국_데이터_검토_시기]]
