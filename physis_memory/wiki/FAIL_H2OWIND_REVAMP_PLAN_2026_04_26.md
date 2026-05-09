---
type: wiki
created: 2026-05-09
tags: [h2owind, 실패, 폐기, 회고, 학습자료]
ref_count: 0
outcome_score: 0.0
---

# FAIL_H2OWIND_REVAMP_PLAN_2026_04_26

> 🔴 실패·폐기·롤백 흔적
> 재정비 계획 — 무엇이 잘못됐기에 재정비?
> 출처: `/home/nas/H2OWIND_2/docs/REVAMP_PLAN_2026-04-26.md`

# 팝아이즈 전면 개편 기획안 — IA + 피지수 자동화 파이프라인 동시 수리

> **기안**: 이순신 (李舜臣), H2OWIND 수도 지국 단군
> **수신**: 창조주 방부장 / 본영 단군
> **기안일**: 2026-04-26 KST
> **상태**: 🟡 **결재 대기** (코드 변경 전 HARD-GATE)
> **근거**: 2026-04-26 방부장 명 4건 — (1) 통합·팀별 현황 IA 개편 (2) 그 외 바꿔야 할 부분 (3) Phase 3·4 미작동 (4) Phase 2 동우 양식 과결합

---

## 0. 한 줄 결론

**현재 팝아이즈는 "정적으로는 Phase 1~4 완료, 실측으로는 Phase 3 이하 전부 침묵"의 상태**입니다. 근본 원인은 한 가지 — **Drizzle 마이그레이션에 `DailyWorker`·`DailyTeamSummary` 테이블이 누락**되어 그 위에 쌓은 Phase 4·5가 매일 "0건 적재" 알림만 발송하고 있습니다. IA 어긋남(일보요약이 팀별현황 안에 묻힘)은 별개의 두 번째 문제입니다.

---

## 1. 진단 요약 — 증거 기반

### 1-A. 백엔드 — 피지수 공사일보 자동화 파이프라인

| Phase | 정적 진행 | 실작동 | 원인 (코드 인용) |
|---|---|---|---|
| **Phase 1** 데이터 수집 | ✅ 완료 | ⚠️ 미검증 | `inface_connector.py`·`turso_reader.py` 존재. 인페이스 API 실호출 검증 부재 |
| **Phase 2** Excel 생성 | ✅ 완료 | ❌ 양식 종속 | [scripts/tools/excel_generator.py](../scripts/tools/excel_generator.py): `SITE_NAME` 라인 19 하드코딩, `BLOCK_SIZE=50` 라인 20, 4블록 좌표 `[1,6,11,16]` 라인 110, 셀 병합 `A1:T1` 등이 **동우건설 양식에 완전 결합** |
| **Phase 3** Turso 적재 | ❌ **테이블 누락** | ❌ | [drizzle/meta/_journal.json](../drizzle/meta/_journal.json) 마이그레이션 0000~0005에 `DailyWorker`·`DailyTeamSummary` **정의 없음**. `0003_parallel_firebrand.sql`엔 `DailyWorkLog`·`DetailReport`·`ExcelColorRule`만 있음. **커밋 `99e83d0`은 Drizzle 스키마 코드만 추가하고 마이그레이션 SQL 생성·푸시는 안 함** |
| **Phase 4** LangGraph | ✅ 완료 | ❌ 매일 0건 | [scripts/daily_report_graph.py](../scripts/daily_report_graph.py) 라인 157~159 `turso_node` SQL 에러 → 라인 161~163 catch → `turso_inserted: 0`로 텔레그램 알림. 실제 적재 0건 |
| **Phase 5** 스케줄러 | ⚠️ 진입점만 | ❌ | `run_daily_report.py` 정상 호출 가능. Phase 3 막힘으로 실효 없음 |

**근본 원인 한 줄**: `npx drizzle-kit push` 실행 흔적이 없거나, 스키마 코드에서 SQL 마이그레이션이 생성되지 않았음. 그 결과 운영 DB에 테이블이 없는 채로 INSERT만 시도되고 있음.

### 1-B. 프론트엔드 — 통합/팀별 현황 IA

**Header 네비** ([app/components/Header.tsx:17-26](../app/components/Header.tsx#L17-L26)):
```
대시보드(/) · 출역기록(/reports) · 인원관리 · 자재관리 · 안전관리 · 정산관리 · 통계 · 설정
```
→ **공사일보 전용 메뉴 없음** (출역기록은 보관함 성격)

**홈(`/`) 메인 탭** ([app/page.tsx:1673-1686](../app/page.tsx#L1673-L1686)):
1. 통합현황 (`activeTab='overview'`)
2. **팀별현황** (`activeTab='teams'`) ← 일보가 여기 묻힘
3. 장비관리 / 공정표 / 타설현황 / 가설관리

**팀별현황 서브탭** ([app/page.tsx:2166-2171](../app/page.tsx#L2166-L2171)):
- 1P 출력명단 (`workers-list`)
- **2P 일보요약 (`summary`)** ← 방부장 지적 지점
- 3P 팀별분석 (`analysis`) — *지국장 보고: 미작동*
- 4P 총괄정산 (`settlement`) — *지국장 보고: 미작동*

**중복·분산**:
- `/reports` (보관함) vs `/reports/new` (단일 작성기, 미사용) vs `/team/input` (팀 일보 작성) vs `/workers/teams` (공종 마스터) — 네 개가 비슷한 도메인을 4갈래로 흩뜨림

### 1-C. 검증 인프라

| 항목 | 결과 |
|---|---|
| 빌드 | ✅ exit 0 (운영 가동에 직접 장애 없음) |
| Jest 테스트 | ❌ **부팅조차 실패** — `generated/client/package.json`의 BOM 문자로 jest-haste-map 파싱 오류. 테스트 10개 전부 미실행 |
| ESLint | ⚠️ **471 errors / 1748 warnings (174 파일)** — 대부분 `@typescript-eslint/no-explicit-any` |

---

## 2. 개편 방안

### 2-A. IA 재설계 (방부장 지시 직격)

**원칙**: 사용자 멘탈 모델 = "통합 → 일보 → 팀별 → 부속".

**Before → After**

| | Before (현재) | After (제안) |
|---|---|---|
| 메인 탭1 | 통합현황 | 통합현황 (그대로) |
| 메인 탭2 | 팀별현황(서브: 출력명단/**일보요약**/팀별분석/총괄정산) | **공사일보** (구 2P 일보요약을 단독 탭으로 승격) |
| 메인 탭3 | 장비관리 | **팀별현황** (서브: 출력명단/팀별분석/총괄정산 — 일보요약 빠짐) |
| 메인 탭4~7 | 공정표/타설/가설 | 장비관리/공정표/타설/가설 (그대로) |
| Header 네비 | 대시보드/출역기록/... | 대시보드/**공사일보**/출역기록/... (별도 진입점 추가, 홈 탭과 동일 컴포넌트로 라우팅) |

**상태관리 정비** (`lib/store.ts`의 `activeTab`·`teamSubTab`):
- `activeTab` enum에 `'daily-report'` 추가, `'teams'`는 유지
- `teamSubTab`은 `'workers-list'|'analysis'|'settlement'` 3개로 축소 (`'summary'` 제거)
- `summary` 모드의 `<TeamDailyOutputSection mode="summary">`를 새 `app/components/DailyReportPanel.tsx`로 추출 → `activeTab='daily-report'`에서 렌더

**예상 변경 파일**: `app/page.tsx` (탭 분기), `app/components/Header.tsx` (네비 추가), `lib/store.ts` (탭 enum), 새 `app/components/DailyReportPanel.tsx`. 약 4~5 파일.

### 2-B. 백엔드 — 피지수 파이프라인 수리 4축

#### 축 1. **DB 테이블 즉시 신설** (긴급, 차단 해소)
- `drizzle/0006_add_daily_tables.sql` 작성:
  ```sql
  CREATE TABLE IF NOT EXISTS DailyWorker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    team TEXT NOT NULL,
    jobType TEXT,
    workerName TEXT NOT NULL,

## 분류
- 지국: h2owind
- 유형: 실패/폐기/응급복구
- 가치: 미래 해답을 위한 비싼 학습 자료

## 연결
- [[홍익인간]]
- [[3지국장_정체성]]
- [[FAIL_종합_분석]]


## 연결

- [[홍익인간]]
