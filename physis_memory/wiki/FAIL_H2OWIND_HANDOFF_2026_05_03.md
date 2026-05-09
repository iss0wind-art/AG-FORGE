---
type: wiki
created: 2026-05-09
tags: [h2owind, 실패, 폐기, 회고, 학습자료]
ref_count: 0
outcome_score: 0.0
---

# FAIL_H2OWIND_HANDOFF_2026_05_03

> 🔴 실패·폐기·롤백 흔적
> H2OWIND 핸드오프 (실패 사례 포함)
> 출처: `/home/nas/H2OWIND_2/HANDOFF_2026-05-03.md`

# HANDOFF — 2026-05-03 (이순신)

> 본영 단군 / 다음 세션 이순신을 위한 인계서.
> 직전 세션: `feat(labor-investment): 투입비 분석 양식 + 인페이스 파이프라인 복구` (commit `e17747a`).

---

## 1. 이번 세션 요약

### 신설 — 투입비 분석 페이지 (`/labor-investment`)
출역기록 메뉴를 대체. PDF "도급 투입비 분석" 양식 자동 생성.

- **UI**: [형틀1~4 탭] · [좌측 동 사이드바] · [상단 층 탭] · [우측 양식]
- **사이드바 색칠**: 활성 팀이 작업한 동만 진하게 (DailyWorkLog 기반)
- **층 탭 동적**: 동마다 가능한 층(B2F/B1F/1F/.../기초/버림/PIT/RF)을 자동 결정
- **메타 수동 입력**: 물량/금액/날짜 → 옅은 노란색 셀 + localStorage 자동 저장 (key: `lab-inv-meta:{팀}:{동}:{층}`)

### API 신설 (5개)
| 라우트 | 역할 |
|---|---|
| `GET /api/buildings` | DashboardStore.concrete_data → 동 목록 16개 |
| `GET /api/teams/leaders` | Worker WHERE role='팀장' → {teamId: name} |
| `GET /api/labor-investment` | DailyWorkLog 슬라이스 + segment 파서 + 인페이스 보강 |
| `GET /api/labor-investment/team-zones` | 팀별 작업 동 set |
| `POST /api/reports/inface-process` | InfaceRawData → DailyWorker 적재 |

### 데이터 파이프라인 복구
| 항목 | 변경 |
|---|---|
| DailyWorker | **0건 → 8,250행 / 38일** (인페이스 재처리) |
| 팀명 정규화 | `형틀1(문성용팀)`→`형틀1` 등 4,641행 일괄 정리 |
| 헤더 오염 | `04/xx`/name=`-` 24건 삭제 |
| 김용환 | role=null → `팀장`, teamId='형틀4' (직접 SQL) |
| InfaceRawData | date에 UNIQUE 인덱스 추가 (excel-import ON CONFLICT 안정화) |

### 도메인 룰 (방부장 승인)
1. **Segment 분할**: `' / '` (공백 양쪽)만 구분자 → `E/V`, `T/C` 약어 보호
2. **층 정규화**: `지하2층`→`B2F`, `지하1층`→`B1F`, `지상N층`→`NF`, `옥상`/`지붕`→`RF`, `PIT`/`기초`/`버림`/`매트` 별도
3. **인원 추출**: `(N)` / `(N명)` / `(N공수)` segment 끝 괄호
4. **인페이스 보강**: 같은 날 모든 작업이 단일 동에서 + 명시 인원 없을 때 → `[인페이스 N공수]` 합계행 인원을 그 동에 100% 귀속 (보강률 ~90%)
5. **분배 추정**: segment 일부에만 인원 명시 → 빨간색 굵게 + tooltip "분배 추정"
6. **기초/버림/매트**: 비고 분리 폐지, 층 탭에서 직접 선택

---

## 2. 코드 리뷰 결과 (보강 필요)

### CRITICAL
- **C1 [route.ts:137-146]** SQL LIKE 와일드카드(`%`, `_`) escape 누락. 현재 dong이 숫자 정규화로 우연히 막혀있으나, 알파벳 허용 시 즉시 깨짐.
  ```ts
  const likeEsc = (s: string) => s.replace(/[\\%_]/g, '\\$&');
  // ... LIKE ? ESCAPE '\\'
  ```

### HIGH
- **H1 [page.tsx:89]** localStorage 키에 **siteId 누락**. 다중 현장 시 충돌. 하드코딩 "금호 부산 에코델타시티 24BL"도 동일 이슈. → `NEXT_PUBLIC_SITE_ID` prefix 추가 + 향후 DB 마이그레이션.
- **H2 [route.ts:194-209]** 분배 추정 시 `mainSegs.length>1`인데 일부만 인원 표기된 경우, 누락 segment의 인원이 **0으로 집계**되어 합계 누락. 인페이스 합계 - explicitSum으로 보충 가능하면 보충 필요.
- **H3 [page.tsx:101]** 초기화 effect deps 빈 배열 → ESLint disable 주석 명시.
- **H4 [inface-process/route.ts:155-158]** drizzle `boolean` vs raw SQL `processed = 1` 혼용. drizzle ORM으로 통일.

### MEDIUM (요약)
- M1: number input controlled value의 0/'' 모호성
- M2: localStorage 매 keystroke 저장 → 디바운스 필요
- M3: 인원 정규식이 소수(`12.5명`) 미지원
- M4: `availableFloors`에서 층 미표기 segment 카운트 stats 노출
- M5: pickItem `count = Number(x) || 1.0` → 0이 1로 둔갑
- M6: `catch (e: any)` → `unknown` 통일
- M7: `onConflictDoNothing()` 실 inserted 카운트와 응답 불일치

### LOW
- L1: 단가 19500/18000/21000/20000 매직넘버 → `lib/labor-investment-constants.ts`
- L2: rowCapacity=34 상수화
- L5: inface-process의 DELETE→INSERT→UPDATE 트랜잭션화

### Strengths
- segment splitter `\s+\/\s+` 보호 정규식 정확
- 인페이스 단일 동 100% 귀속의 보수적 설계 (모호 시 null)
- workersGuessed 빨간색 + tooltip
- AbortController cleanup 일관 적용
- InfaceRawData.date UNIQUE 인덱스로 ON CONFLICT 안정화
- normalizeTeam 정규화 룰
- floorPatterns 우선순위 배열 (기초/버림이 일반 층보다 먼저)

---

## 3. 다음 세션 우선순위

### 즉시 (이번 주)
1. **H1 — 다중 현장 대응** localStorage 키에 siteId 추가
2. **H2 — 분배 추정 누락 보충** `infaceTotal - explicitSum` 잔여를 낮은 동에 몰음
3. **C1 — LIKE escape**

### Phase 2 (메뉴 본격화)
4. **복구 2: 승인 화면 (DailyConfirmed)** — 인페이스 + 팀장 대시보드 → 관리자 승인 → DailyConfirmed INSERT 흐름. *원래 워크플로우가 미구현 상태였음.*
5. **복구 3: inface-finalize 시 processed=1 강제** — 현재 1건 unprocessed 잔존
6. **메타 영구 저장** — localStorage → DB 테이블 (`InvestmentMeta`) 마이그레이션
7. **Worker.externalId 매칭** — 현재 inface-process에서 matched=0. Worker 마스터에 externalId 채우기

### 도면 표시 (사용자 결정 대기)
사용자가 WebGL 사용 의향. 권장 경로:
- **A**: PNG/JPG 캡처 → 동별 폴더 (`drawings/101동.png` 등) 가장 단순
- **B (권장)**: SVG 한 장 + 동별 `<g id="101동">` 그룹 → React에서 hover/클릭/색상
- **C**: glTF/GLB + three.js (3D 입체) 오버킬

원본 포맷(DWG/PDF/Revit) 확인 후 변환 경로 결정 필요.

---

## 4. 알려진 한계 (사용자 인지)

| 항목 | 상태 |
|---|---|
| `T/C #6 버림틀` 같이 **동 식별 안 되는 segment** | 본 행/비고 모두 안 들어감

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
