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

# H2OWIND_docs_v6-features

> 출처: `H2OWIND_2/docs/v6-features.md` — 2지국 H2OWIND (이순신) 자동 흡수
> 흡수일: 2026-05-09

﻿# 팝아이즈 V6.0 기능 설명서

> 구현 완료: 2026-04 | 총 9개 모듈

---

## 1. 팀별현황 (A안: 전주 동일 요일 대비)

**위치**: 통계 → 🏗️ 팀별현황 탭

**기능**
- 오늘 날짜와 전주(7일 전) 동일 요일을 비교하여 팀별 인원 증감을 표시
- 팀별 카드: 오늘 인원 / 전주 인원 / 증감(△/▽) / 당일 작업내용 요약

**API**
- `GET /api/stats/team-status`
- `dailyOutputs` 테이블에서 오늘 + 전주 데이터 조회
- `teamReports`에서 작업내용(content) 조인

**관련 파일**
- `app/api/stats/team-status/route.ts`
- `app/stats/page.tsx` (TeamStatusData 인터페이스, teamStatus 탭)

---

## 2. 타설현황 자동 파싱

**위치**: 메인 홈 → 콘크리트 탭 → 타설 파싱 로그

**기능**
- `DailyWorkLog`와 `TeamReport`에서 '타설' 키워드 자동 필터
- 자유형식 한국어 텍스트에서 동/층/물량(㎥) 정규식 추출
- 신뢰도 점수 (0~100):
  - 🟢 80 이상: 자동 승인
  - 🟡 50~79: 노란 행 (수동 확인 권장)
  - 🔴 49 이하: 빨간 행 (수동 승인 필요)
- 수동 승인 버튼 제공

**API**
- `GET /api/concrete/parsed-log`

**관련 파일**
- `app/api/concrete/parsed-log/route.ts` (parsePourContent 함수 포함)
- `app/components/ConcreteParsedLog.tsx`
- `app/page.tsx` (콘크리트 탭에 삽입)

---

## 3. 가설관리 CRUD 완성

**위치**: (가설관리 페이지)

**기능**
- 기존 GET/POST에 PUT(수정), DELETE(삭제) 추가
- 가설 계획서 및 가설재 양쪽 모두 완전한 CRUD

**API**
- `PUT /api/temporary-works/plans` — 계획 수정
- `DELETE /api/temporary-works/plans?id=` — 계획 삭제
- `PUT /api/temporary-works/materials` — 자재 수정
- `DELETE /api/temporary-works/materials?id=` — 자재 삭제

**관련 파일**
- `app/api/temporary-works/plans/route.ts`
- `app/api/temporary-works/materials/route.ts`

---

## 4. 출역 원장

**위치**: 근로자 관리 → 원장 탭

**기능**
- 이름 / 기간(from~to)으로 근로자별 출역 이력 검색
- 날짜별 테이블: 날짜 / 팀명 / 작업내용
- 요약: 총 출역일수 / 첫 출역일 / 마지막 출역일
- 팀장 카드 드래그&드롭 → 소속 팀 변경 (`/api/site/orgchart` PUT 호출)

**API**
- `GET /api/workers/ledger?name=&from=&to=`
- `reportWorkers` → `teamReports` → `workers` 3-table 조인

**관련 파일**
- `app/api/workers/ledger/route.ts`
- `app/workers/page.tsx` (ledger 뷰모드, 드래그&드롭 로직)

---

## 5. 대시보드 차트

**위치**: 통계 → 📈 대시보드 탭

**기능 (3개 차트)**
1. **예산 소진율** — 팀별 수평 바차트 (계약금 대비 소진액 %)
2. **진행률 추세** — SVG 폴리라인 (최근 30일 누적 공수)
3. **자재 TOP5** — 월별 수직 바차트 (청구 건수 기준)

**API**
- `GET /api/stats/dashboard-summary`
- 계약(contracts), 일일 출력(dailyOutputs), 자재청구(materialRequests) 통합 조회

**관련 파일**
- `app/api/stats/dashboard-summary/route.ts`
- `app/stats/page.tsx` (dashboard 탭, SVG 렌더링)

---

## 6. TBM 교육자 입력형 서명

**위치**: 안전관리 → TBM 일지

**기능**
- 교육자 이름을 직접 입력 (기존 하드코딩 '김희찬' 제거)
- 이름 입력 시 서명란과 스탬프 동적 생성
- `SignatureStamp` 컴포넌트 재사용

**관련 파일**
- `app/components/safety/TBMLog.tsx` (instructorName state 추가, line ~588)

---

## 7. 자재 조기발주 경보 + 일괄처리

**위치**: 자재관리 → ⚡ 일괄처리 탭

**기능**
- 조기발주 경보: 상태='청구' + 키워드 매칭(레미콘/펌프카/크레인/비계/동바리 등) + 21일 이내 → 오렌지 배너
- 일괄처리: 체크박스 다중 선택 → 일괄 배송완료 / 일괄 반려

**API**
- `PATCH /api/materials` — `{ ids: string[], status }` 형태로 일괄 업데이트

**관련 파일**
- `app/api/materials/route.ts` (inArray 일괄 PATCH 추가)
- `app/materials/page.tsx` (bulk 탭, earlyOrderWarnings, handleBulkStatus)

---

## 8. 서식관리 QR 다국어

**위치**: 안전관리 → 📋 서식 탭

**기능 (2파트)**

### 카드 QR 코드
- 서식 카드마다 Google Charts QR API로 QR 이미지 표시
- QR URL → `/safety/forms/[id]` (모바일 뷰어 직접 링크)
- "보기" 버튼 (모바일 뷰어 새탭) + "다운로드" 버튼 분리

### 모바일 다국어 뷰어
- URL: `/safety/forms/[id]`
- 4개 언어 탭: 한국어 / 中文 / Tiếng Việt / Русский
- 같은 이름의 다른 언어 버전 자동 탐색
- PDF → iframe, 이미지 → img, 기타 → 다운로드 링크
- 하단 서명 안내 다국어 표시

**관련 파일**
- `app/safety/page.tsx` (카드 QR 코드, 보기/다운로드 버튼)
- `app/safety/forms/[id]/page.tsx` (모바일 뷰어 신규)

---

## 9. 정산 원스톱 청구

**위치**: 정산관리 → ⚡ 원스톱 청구 탭

**기능**
- 팀 선택 + 기간(from~to) → 조회 버튼 클릭 한 번으로:
  1. **출역 공수 내역**: 날짜별 인원수, 근로자 목록(펼치기), 일당 × 인원 소계
  2. **자재 청구 내역**: 자재명/규격/수량/단위/상태/날짜 테이블
  3. **노무비 합계**: 총 공수 × 평균 일당 자동 계산
- 계약 단가 미등록 시 경고 배너
- 🖨️ 인쇄/PDF 버튼 (window.print)

**API**
- `GET /api/settlement/onestop?team=&from=&to=`
- `contracts` + `teamReports` + `reportWorkers` + `workers` + `materialRequests` 통합 조회

**관련 파일**
- `app/api/settlement/onestop/route.ts`
- `app/components/SettlementOneStop.tsx`
- `app/settlement/page.tsx` (원스톱 청구 탭 추가)

---

## 공통 참고

| 항목 | 내용 |
|------|------|
| DB | Turso (LibSQL) + Drizzle ORM |
| 스키마 | `db/schema.ts` |
| 빌드 | `npm run build` |
| 서버 가동 | `가동_서버_및_지록.bat` |
| 포트 | 3000 (메인), 3001 (BOQ) |


## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]
