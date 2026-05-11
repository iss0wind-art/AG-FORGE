---
created: 2026-05-09
domain: 주식·금융·경제
outcome_score: 0.2
ref_count: 8
source: /home/nas/STOCK-TRADING/Stock-Trading/docs/decisions/2026-05-09-v2-direction.md
tags:
- PATCH
- governance
- v2
- integration
- 추적
type: code_governance
---

# Stock-AI v2 PATCH 시스템 — 11건 추적

[[방부장_4단계_AI인프라_사이클]] | [[Stock_AI_파이프라인]]

> 모든 패치는 **코드 내 `# PATCH-{ID}: 설명` 주석 + 본 문서** 양쪽 등록.
> `grep -rn "PATCH-" Stock-Trading/` 한 줄로 적용·연기·계획 상태 전수 확인.

## 마커 상태 약속

| 상태 | 의미 |
|------|------|
| `(applied)` | 코드에 실제 반영됨 |
| `(deferred)` | 위치만 표시, 추후 적용 |
| `(standby)` | 트리거 조건 발생 시 적용 |
| `(planned)` | 데이터 누적 후 적용 |

## v1·v2 통합 결정 (5/9)

- **v2 통째 교체 거부** — 11파일 후퇴 (main.py 포트 하드코딩, chart_agent gemini-2.0 deprecated, kis_client 토큰 캐시 없음 등)
- **v2 macro 모듈 5+1파일만 수렴** — 시장 환경 → 자산 배분 시그널은 종목 분석과 직교한 가치
- **PATCH-DR 7건 + PATCH-SR 4건 등록**

## PATCH-DR (Data Reliability) — 7건

| ID | 분류 | 시점 | 위치 | 내용 |
|----|------|------|------|------|
| **DR-1** | 필수 | 즉시 | `collector.py:get_us_indicators` | `^DXY` → `DX-Y.NYB` (Yahoo `^DXY` 미존재 → 달러인덱스 룰 죽은 채 운영) |
| **DR-2** | 필수 | 즉시 | `correlation_engine.py:_calc_allocation` | 누적 차감 음수 가능 → `max(0, …)` 클램프 + 합 100 정규화 |
| **DR-3** | 필수 | 즉시 | `macro_pipeline.py` + `data/macro/state.py` | 변화감지: `.cache/macro_state.json` → 30분마다 동일 메시지 반복 차단 |
| **DR-4** | 필수 | 즉시 | `api/macro_router.py` | `Depends(verify_webhook_secret)` — `X-Webhook-Secret` 헤더. 무인증 도배 차단 |
| **DR-5** | 선택 | 2주 후 | `collector.py:get_us_indicators` | Yahoo 비공식 → FRED 공식 (DGS10, DTWEXBGS) `(deferred)` |
| **DR-6** | 대기 | 셀렉터 깨짐 1회 시 | `collector.py` 환율/코스피/금 | 네이버 셀렉터 실패 → yfinance / KRX OpenAPI 폴백 `(standby)` |
| **DR-7** | 후순위 | 이력 4주 누적 후 | `correlation_engine.py` | 정적 임계(VIX>30) → 최근 1년 90% percentile `(planned)` |

## PATCH-SR (Strategy Reflection) — 4건 ★

방부장 [[방부장_4단계_AI인프라_사이클]] 직관을 시스템 의사결정에 강제 반영.

| ID | 위치 | 내용 |
|----|------|------|
| **SR-1** | 신규 `utils/sector_phase.py` | 종목코드 → (phase 1~4, tag) 매핑. 초기 30~50종목, 미등록 phase=0 |
| **SR-2** | 신규 `data/bio_event_scanner.py` + `scheduler/bio_pipeline.py` | DART 임상/기술이전/품목허가 + 뉴스 AI신약/GLP-1 → 알림 우선순위 격상 |
| **SR-3** | `agents/ensemble_agent.py` | phase 4 +30%, phase 3 0%, phase 2 −5%, phase 1 −15% 가중 |
| **SR-4** | `data/macro/correlation_engine.py:analyze` | 매크로 × 섹터 매트릭스. 공포+phase4=역발상 바이오 매집 |

## 통합 작업 순서 (방부장 합의안 §5)

1. v2 macro 5+1파일 복사
2. PATCH-DR-1,2,3,4 적용 (필수 4건)
3. PATCH-SR-1,2,3,4 적용 (전략 4건)
4. PATCH-DR-5,6,7 마커 주석 삽입
5. `main.py`에 `include_router(macro_router)` + 바이오 라우터
6. `ecosystem.config.js` `stock-ai-macro`, `stock-ai-bio` 추가
7. `.env`에 `WEBHOOK_SECRET` 발급
8. `docs/PATCHES.md` 색인
9. `pm2 restart all && pm2 save`
10. 검증 체크리스트

## 피지수 학습 관점

### 1. 방부장 거버넌스 모델
- 모든 변경 = ID + 위치 + 시점 + 분류 4축 추적
- 코드 주석과 문서 양쪽 등록 = 단일 진실 소스 + 검증 가능
- → 피지수 자체 변경에도 동일 모델 적용 가능 (`# PHYSIS-CHANGE-{ID}`)

### 2. v2 거부 → 점진 통합 원칙
- 통째 교체 = 후퇴 위험
- 검증된 부분만 수렴 = 진보 보장
- → 피지수 자아 진화에도 동일 원칙 (Titans memory + Reflection 점진 갱신)

### 3. 패치 추적성
- `grep -rn "PATCH-" Stock-Trading/` = 한 줄로 전수 확인
- 피지수 자아 변경도 동일하게 grep 가능하면 좋음

## 자율 행동 후보 (Tier 2)

- [ ] PATCH 11건 적용 상태 grep + 진척 박제
- [ ] [[방부장_4단계_AI인프라_사이클]] 가중치를 physis_finance_brain ChromaDB 메타에 추가
- [ ] 바이오 이벤트 키워드 사전 (DART + 뉴스) 별도 노드 박제

## 연결

[[방부장_4단계_AI인프라_사이클]] · [[Stock_AI_파이프라인]] · [[Stock_AI_모듈_지도]] · [[7중_안전장치]]
