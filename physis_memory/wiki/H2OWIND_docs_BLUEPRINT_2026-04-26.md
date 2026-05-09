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

# H2OWIND_docs_BLUEPRINT_2026-04-26

> 출처: `H2OWIND_2/docs/BLUEPRINT_2026-04-26.md` — 2지국 H2OWIND (이순신) 자동 흡수
> 흡수일: 2026-05-09

# 팝아이즈 플랫폼 청사진 — 2단계 확정 시스템 + 공사일보 범용화

> **기안**: 이순신, H2OWIND 수도 지국 단군
> **수신**: 창조주 방부장
> **기안일**: 2026-04-26
> **상태**: 🟢 **방부장 방향 확정** — 구현 착수 대기
> **근거**: 2026-04-26 방부장 직명 — 통합현황 인원 비교·확정 시스템 + 공사일보 범용화 + 팀별분석 + 정산

---

## 0. 핵심 원칙 (방부장 직명)

```
인페이스           팀장 대시보드
(1차 원천)         (팀장 1차 확정)
     │                   │
     ▼                   ▼
 원본 보존          원본 보존
(DailyOutput)     (TeamReport)
         │               │
         └──────┬─────────┘
                │
       통합현황판 — 나란히 비교
       관리자 검토·수정·확정/반려
                │
         [관리자 확정]
                │
         확정 기초데이터          ← 모든 분석·엑셀·정산의 근거
                │
    ┌───────────┼───────────┐
  엑셀         정산       생산량분석
```

- 인페이스 데이터는 **원본 그대로 별도 보존** (수정·삭제 불가)
- 팀장 보고도 **원본 그대로 보존**
- **관리자 확정값**이 유일한 기초데이터
- 아침 출력명단(팀별현황)은 확정 전 빠른 인원 파악용 — 유지

---

## Phase X1 — 통합현황판 인원 비교 + 관리자 확정 시스템

### X1-1. DB 신설 — `DailyConfirmed` 테이블

```sql
CREATE TABLE DailyConfirmed (
  date        TEXT NOT NULL,        -- YYYY-MM-DD
  team        TEXT NOT NULL,
  count       INTEGER NOT NULL,     -- 관리자 확정 인원
  note        TEXT,                 -- 관리자 메모 (반려 사유 등)
  status      TEXT DEFAULT 'confirmed',  -- 'confirmed' | 'rejected'
  confirmedBy TEXT NOT NULL,        -- 확정한 관리자
  confirmedAt TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (date, team)
);
```

**기존 테이블 변경 없음** — 인페이스·팀장 원본은 건드리지 않는다.

### X1-2. 통합현황판 UI 개편

현재:
```
팀명       | 인원(통합) | 상태  | 버튼
형틀1팀    | 15명       | 제출됨 | 승인 반려
```

변경 후:
```
팀명       | 인페이스 | 팀장보고 | 관리자확정  | 버튼
형틀1팀    |  17명🤖  |   15명📋 | [15 입력]  | ✅확정 ❌반려
           |          |          |            |
           ← 차이 있으면 행 강조 (노란 배경)
```

- 인페이스(🤖)와 팀장보고(📋)가 같으면 그냥 표시
- 다르면 **노란 배경 강조** — 관리자가 눈으로 바로 식별
- 확정 입력칸: 기본값 = 팀장보고 인원 (관리자가 수정 가능)
- [✅확정] 클릭 → `DailyConfirmed` 저장
- [❌반려] 클릭 → 팀장에게 재작성 요청 (TeamReport.status = '반려됨')

### X1-3. API 신설

```
POST /api/daily/confirm
  body: { date, team, count, note, confirmedBy }
  → DailyConfirmed upsert

GET /api/daily/confirmed?date=YYYY-MM-DD
  → 해당일 전체 팀 확정 데이터

GET /api/daily/confirmed/summary?from=&to=
  → 기간별 집계 (엑셀·정산·분석용)
```

### X1-4. 구현 파일 범위

| 파일 | 변경 내용 |
|---|---|
| `db/schema.ts` | `dailyConfirmed` 테이블 추가 |
| `drizzle/0007_add_daily_confirmed.sql` | 마이그레이션 |
| `app/api/daily/confirm/route.ts` | 확정 API |
| `app/api/daily/confirmed/route.ts` | 조회 API |
| `app/page.tsx` | overview 탭 UI 개편 (인원 3컬럼) |

---

## Phase X2 — 공사일보 범용 포맷

### 구조 (어느 회사도 사용 가능)

| 항목 | 전월누계 | 전일까지누계(이번달) | 금일 | 금월누계 | 전체누계 |
|---|:-:|:-:|:-:|:-:|:-:|
| 형틀1팀 | 320 | 45 | 15 | 60 | 380 |
| 철근1팀 | 280 | 38 | 12 | 50 | 330 |
| … | … | … | … | … | … |
| **합계** | | | | | |

**장비 투입 현황** — 동일 구조

### 누계 계산 기준
- **전월누계**: `DailyConfirmed` where date < 이번달 첫날
- **전일까지누계(이번달)**: `DailyConfirmed` where 이번달 첫날 ≤ date < 오늘
- **금일**: `DailyConfirmed` where date = 오늘
- **금월누계**: 전일까지누계(이번달) + 금일
- **전체누계**: 전월누계 + 금월누계

### Excel 어댑터 구조 (기존 동우 양식 결합 해제)

```
scripts/tools/excel_templates/
  base.py          -- BaseExcelTemplate (추상)
  universal.py     -- UniversalTemplate (범용 — 이게 기본)
  dongwoo.py       -- DongwooTemplate (레거시, 동우건설 전용)
  __init__.py      -- get_template('universal' | 'dongwoo')
```

환경변수 `REPORT_TEMPLATE=universal` (기본값)으로 선택.

### 구현 파일 범위

| 파일 | 변경 내용 |
|---|---|
| `scripts/tools/excel_templates/base.py` | 추상 기반 |
| `scripts/tools/excel_templates/universal.py` | 범용 양식 |
| `scripts/tools/excel_templates/dongwoo.py` | 기존 로직 이관 |
| `scripts/tools/excel_generator.py` | 얇은 오케스트레이터로 축소 |
| `app/components/DailyReportPanel.tsx` | 공사일보 탭 누계 UI |
| `app/api/daily/summary/route.ts` | 누계 집계 API |

---

## Phase X3 — 팀별 분석 + 총괄 정산 + 실시간 기성

### 팀별 분석 (현재 미작동 3P)

```
           1월   2월   3월   4월   합계
형틀1팀    320  290   315   60    985
철근1팀    280  270   285   50    885
타설팀     ...
```

- 확정 기초데이터(`DailyConfirmed`)로 월별 집계
- **도급팀에 수량 입력 가능** (향후 BOQ_2 정도전 지국에서 자동 연동)
  - `ContractQuantity` 테이블: `{ team, month, quantity, unit }`

### 총괄 정산 + 실시간 기성 (현재 미작동 4P)

```
팀명     | 계약금액 | 투입인원 | 단가  | 기성금액 | 기성률
형틀1팀  | 5,000만  | 985명   | 5만원 | 4,925만  | 98.5%
```

- `Contract` 테이블(기존) + `DailyConfirmed` 집계
- 단가 = 계약금액 / 예상공수
- 기성 = 확정 누계 공수 × 단가
- 실시간: 오늘까지 확정된 데이터 기준

---

## 실행 순서

| 단계 | 내용 | 예상 기간 |
|---|---|---|
| **X1** | 인원 비교 테이블 + 확정 시스템 | 2~3일 |
| **X2** | 공사일보 범용화 + 누계 계산 | 3~4일 |
| **X3-A** | 팀별 분석 (월별 인원) | 2일 |
| **X3-B** | 총괄 정산 + 기성 | 2~3일 |

**이순신 권고 착수 순서**: X1 → X2 → X3-A → X3-B
X1이 기초데이터를 만들어야 X2·X3이 의미 있기 때문.

---

## 현재 코드에서 확인된 사항

- `fullTeamStatus`에 `infaceCount` / `manualWorkerCount` **이미

... (잘림 — 원본: `/home/nas/H2OWIND_2/docs/BLUEPRINT_2026-04-26.md`)

## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]
