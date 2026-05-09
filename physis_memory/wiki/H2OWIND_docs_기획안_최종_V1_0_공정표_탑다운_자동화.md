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

# H2OWIND_docs_기획안_최종_V1_0_공정표_탑다운_자동화

> 출처: `H2OWIND_2/docs/기획안_최종_V1.0_공정표_탑다운_자동화.md` — 2지국 H2OWIND (이순신) 자동 흡수
> 흡수일: 2026-05-09

﻿# 팝아이즈 V6.0 공정-타설 통합 엔진 — 최종 기획안
```
문서번호 : [팝-최종기획-260414-001]
수신     : 방부장
발신     : 피지수 팀장
버전     : V1.0 (확정)
작성일   : 2026-04-14
```

---

## 1. 확정 방향 요약

| 항목 | 확정 내용 |
|------|-----------|
| 계산 방향 | Top-down (최상층 → 하부 역산) |
| 기존 데이터 | **절대 불변** — 역산 생성 대상에서 제외 |
| 역산 종료 기준 | 계산된 날짜가 **오늘(today) 이하**가 되는 시점에서 STOP |
| 미확정 계획 | 오늘 이후 자동 생성된 날짜 = **회색(#CCCCCC)** |
| 확정 처리 | 관리자 클릭 → 해당 월 색상 부여 |
| 타설 단위 | 기본: 동-층 단위 단순화 (세대 동일 날 타설) |
| 특수 구간 | B1·지하층·TG보 구간 → 최대 3차 타설 지원 |
| 공정표 자동생성 버튼 | **삭제** (ProjectAutoGanttModal 제거) |
| 데이터 진실 공급원 | `concrete_data` (타설현황) → `gantt_data` 파생 |

---

## 2. 역산 엔진 핵심 로직

### 2-1. 계산 규칙

```
입력: 104동 16F 타설일 = 2026-11-22, 사이클 = 8일

16F: 2026-11-22  → 오늘(04-14) 이후 → 회색으로 생성 ✅
15F: 2026-11-14  → 오늘 이후 → 회색으로 생성 ✅
14F: 2026-11-06  → 오늘 이후 → 회색으로 생성 ✅
...
8F:  2026-07-01  → 오늘 이후 → 회색으로 생성 ✅
7F:  2026-06-23  → 오늘 이후 → 회색으로 생성 ✅
...
xF:  2026-04-15  → 오늘 이후 → 회색으로 생성 ✅
xF:  2026-04-14  → 오늘(today) → STOP ❌ 생성 안함
xF:  2026-04-13  → 오늘 이전 → STOP ❌ 생성 안함

결과: 오늘(2026-04-14) 이전 층들은 건드리지 않는다.
      기존에 입력된 실적 데이터는 그대로 유지.
```

### 2-2. 역산 함수 설계 (Pseudo Code)

```typescript
function calculateTopDown(params: {
  building: string,        // '104동'
  topFloor: string,        // '16F'
  topFloorDate: string,    // '2026-11-22'
  floors: string[],        // ['16F','15F',...,'B1','B2']
  cycleDays: number,       // 8
  today: string,           // '2026-04-14'
  existingData: PourData   // 기존 실적 (불변)
}): PourData {

  const result: PourData = { ...existingData }; // 기존 데이터 복사 (불변 유지)
  const topIndex = floors.indexOf(topFloor);

  for (let i = topIndex; i < floors.length; i++) {
    const stepsFromTop = i - topIndex;
    const calcDate = dayjs(topFloorDate).subtract(stepsFromTop * cycleDays, 'day');

    // STOP 조건: 계산된 날짜가 오늘 이하이면 중단
    if (!calcDate.isAfter(today)) break;

    const key = `${building}-${floors[i]}`;

    // 기존 데이터가 있으면 덮어쓰지 않음
    if (existingData[key]) continue;

    result[key] = {
      date: calcDate.format('YY/M/D'),
      status: 'planned',     // 미확정
      isLocked: false,
      source: 'topdown-auto',
      color: 'gray',
    };
  }

  return result;
}
```

### 2-3. 특수 구간 — 지하층 / TG보 다차 타설

B1, B2, 기초, TG보 구간은 1차~3차 타설이 발생할 수 있음.

```typescript
// 특수 구간 PourCell 구조
interface PourCell {
  date: string,                         // 기본(1차) 타설일
  status: 'actual' | 'planned',
  isLocked: boolean,
  source: 'manual' | 'topdown-auto',
  color?: string,
  phases?: {                            // 다차 타설 (특수 구간 전용)
    phase: 1 | 2 | 3,
    date: string,
    status: 'actual' | 'planned',
    label?: string                      // 예: '1차-벽체', '2차-슬래브'
  }[]
}

// 특수 구간 해당 층 목록 (현장 기준)
const MULTI_PHASE_FLOORS = ['B1', 'B2', '기초', '버림/기초', 'TG보'];
```

UI에서 해당 구간 셀 클릭 시 "차수 추가" 버튼 노출.

---

## 3. 데이터 구조 변경

### 3-1. pourData 키 구조 통일 (핵심 변경)

```
변경 전: 'u1-1-기초'  (unitId 기반) → 공정표와 매핑 불가
변경 후: '101동-기초' (동-층 기반)  → 공정표와 1:1 매핑
```

세대(unit) 정보는 `buildings[].units[]` 에 그대로 보존.
타설 날짜는 동-층 단위로 단일화.

### 3-2. PourData 타입 확장

```typescript
// 변경 전
type PourData = Record<string, string>  // 'u1-1-16F': '26/2/1'

// 변경 후
interface PourCell {
  date: string,                          // 'YY/M/D' 형식 유지
  status: 'actual' | 'planned',          // 실적 vs 미확정 계획
  isLocked: boolean,                     // true = 수정 불가
  source: 'manual' | 'topdown-auto',     // 입력 출처
  color?: string,                        // 확정 시 월별 색상
  phases?: { phase: 1|2|3, date: string, status: string, label?: string }[]
}

type PourData = Record<string, PourCell>  // '101동-16F': PourCell
```

### 3-3. 기존 데이터 마이그레이션 규칙

```typescript
// 기존 unitId 기반 키 → 동-층 기반 키로 변환
// 'u1-1-기초' → '101동-기초'
// 모든 기존 날짜는 status='actual', isLocked=true, source='manual' 로 박제
function migrateOldPourData(old: Record<string, string>, buildings): PourData {
  const result: PourData = {};
  for (const [key, dateStr] of Object.entries(old)) {
    const [, , floor] = key.split('-');         // 'u1', '1', '기초' 파싱
    const buildingIdx = parseInt(key[1]) - 1;   // u1 → 0번째 동
    const buildingName = buildings[buildingIdx]?.name ?? '101동';
    const newKey = `${buildingName}-${floor}`;
    result[newKey] = {
      date: dateStr,
      status: 'actual',
      isLocked: true,
      source: 'manual',
    };
  }
  return result;
}
```

---

## 4. 삭제 항목: ProjectAutoGanttModal

### 제거 대상
- [MonthlyGanttChart.tsx:192](../app/components/MonthlyGanttChart.tsx#L192) — `공정 자동 생성 🚀` 버튼
- [MonthlyGanttChart.tsx:6](../app/components/MonthlyGanttChart.tsx#L6) — `Proj

... (잘림 — 원본: `/home/nas/H2OWIND_2/docs/기획안_최종_V1.0_공정표_탑다운_자동화.md`)

## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]
