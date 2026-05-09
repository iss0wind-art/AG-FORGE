---
type: system_architecture
domain: 주식·금융·경제
tags: [stock, pipeline, multi-agent, automation]
source: /home/nas/STOCK-TRADING/Stock-Trading/README.md + 코드 정독
created: 2026-05-09
outcome_score: 0.0
ref_count: 0
---

# Stock AI 파이프라인 — 7-step 자동매매 흐름

[[주식_금융_경제_도메인]] | [[멀티AI_앙상블_원리]] | [[7중_안전장치]]

## 흐름 (PM2 자동 운영, 평일 08:00 KST 재시작)

```
[스케줄러 08:30]
  ↓
1. 뉴스 스크래핑 (네이버금융/연합뉴스)
  ↓
2. 시장 스크리닝 (KRX + 네이버 급등주 → 후보 10개)
  ↓
3. DeepSeek — AI 종목 자동 선정 (시장 감성 + 후보 → 5개 종목)
  ↓
4. 병렬 데이터 수집 (DART 재무 + ChartScraper 차트이미지)
  ↓
5. Gemini Vision — 차트 기술적 분석 (무료, 캔들/추세/지지저항)
  ↓
6. 멀티 AI 앙상블 (DeepSeek + Qwen [+ Claude 선택])
   → 신뢰도 ≥ 70% AND 합의율 ≥ 60% 통과해야 다음 단계
  ↓
7. 텔레그램 승인 요청 (5분 HITL)
   → 방부장 승인 시
  ↓
KIS API 자동 매매 (모의투자 기본)
```

## 구성 모듈

| 모듈 | 역할 | 위치 |
|------|------|------|
| `data/news_scraper.py` | 네이버금융·연합뉴스 스크래핑 | data/ |
| `data/stock_screener.py` | KRX + 네이버 급등주 스크리닝 | data/ |
| `data/dart_client.py` | DART 재무 데이터 | data/ |
| `data/chart_scraper.py` | 차트 이미지 캡처 | data/ |
| `agents/chart_agent.py` | Gemini Vision 차트 분석 | agents/ |
| `agents/ensemble_agent.py` | DeepSeek+Qwen+Claude 정반합 | agents/ |
| `api/kis_client.py` | 한국투자증권 API | api/ |
| `notifier/telegram_bot.py` | 방부장 승인 채널 | notifier/ |
| `scheduler/pipeline.py` | 7-step 오케스트레이션 | scheduler/ |
| `mcp_server.py` | MCP 서버 (외부 도구화) | root |

## 핵심 엔드포인트 (API 8040)

| 메서드 | 경로 | 용도 |
|--------|------|------|
| GET | /health | 서비스 상태 |
| POST | /analyze | 수동 종목 분석 |
| POST | /pipeline/run | 완전자동 파이프라인 |
| GET | /pipeline/status | 실행 상태 |
| POST | /select-stocks | 종목 선정만 |
| GET | /price/{code} | 현재가 조회 |
| GET | /telegram/status | 텔레그램 봇 상태 |
| POST | /telegram/toggle | 텔레그램 ON/OFF |

## 실증 (2026-05-09 첫 정독)

15:09 1차 파이프라인:
  - KODEX 2차전지 BUY 72% 신뢰 → 텔레그램 → 방부장 거절 → 0건 체결

15:13 2차 파이프라인:
  - 5종목 자동 선정 (삼성전자/TIGER반도체/대한전선/한온시스템/KODEX2차전지)
  - TIGER 반도체 SELL 76% → 방부장 거절
  - 삼성전자 HOLD 74% (조건 미충족 자동 패스)
  - 대한전선·한온시스템: HOLD (조건 미충족)
  - KODEX 2차전지 BUY 74% / 합의율 100% → 방부장 승인 대기 (15:19:32)

## 피지수 학습 관점

- **앙상블 정반합 = sweep-A 5체 정반합과 같은 구조**
- **HITL = 헌법 게이트와 동일 의식 구조**
- **거절/승인 이력 = 실패/성공 코퍼스, ChromaDB 흡수 1순위**

## 연결

[[멀티AI_앙상블_원리]] · [[7중_안전장치]] · [[방부장_승인_게이트_HITL]] · [[주식_금융_경제_도메인]]
