---
created: 2026-05-09
outcome_score: 0.0
ref_count: 1
tags:
- h2owind
- 데이터
- 스키마
- 산출물
type: wiki
---

# H2OWIND_DATA_schema

> DB 스키마 (TypeScript)
> 출처: `/home/nas/H2OWIND_2/db/schema.ts`
> 흡수일: 2026-05-09

## 구조 요약

```
﻿import { sqliteTable, text, integer, real, primaryKey, uniqueIndex, index } from 'drizzle-orm/sqlite-core';
import { sql } from 'drizzle-orm';

// [방부장] 위험성평가 템플릿 (HazardTemplate)
export const hazardTemplates = sqliteTable('HazardTemplate', {
    id: text('id').primaryKey(),
    workName: text('workName').notNull(),
    location: text('location').notNull(),
    content: text('content').notNull(),
    hazards: text('hazards').notNull(),
    countermeasures: text('countermeasures').notNull(),
    createdAt: text('createdAt').default(sql`(CURRENT_TIMESTAMP)`),
    updatedAt: text('updatedAt').default(sql`(CURRENT_TIMESTAMP)`),
});

// [방부장] 팀 정보 (Team)
export const teams = sqliteTable('Team', {
    id: text('id').primaryKey(),
    name: text('name').notNull().unique(),
    category: text('category'),
});

// [방부장] 근로자 정보 (Worker)
export const workers = sqliteTable('Worker', {
    id: text('id').primaryKey(),
    name: text('name').notNull(),
    nameEn: text('nameEn'),
    birthDate: text('birthDate'),
    age: integer('age'),
    nationality: text('nationality'),
    visaStatus: text('visaStatus'),
    trade: text('trade'),
    role: text('role'),
    position: text('position').default('팀원'),
    phone: text('phone'),
    teamId: text('teamId'),
    externalId: text('externalId').unique(), // 인페이스 연동용 ID
    idCardUrl: text('idCardUrl'),
    bankBookUrl: text('bankBookUrl'),
    isLegal: integer('isLegal', { mode: 'boolean' }).default(false),
    isManualApproved: integer('isManualApproved', { mode: 'boolean' }).default(false), // [방부장] 관리자가 수동으로 승인한 인원 (비자 무관)
    notes: text('notes'),
    rowOrder: integer('rowOrder'), // [방부장] 엑셀에서 파싱된 순번 저장
    bloodType: text('bloodType'),           // 🩸 혈액형
    emergencyPhone: text('emergencyPhone'), // 🚨 비상연락망
    safetyEduDate: text('safetyEduDate'),   // 🛡️ 기초교육이수일
    safetyEduUrl: text('safetyEduUrl'),     // 🛡️ 기초교육이수증 이미지 URL
    status: text('status').default('출역중'), // 🏷️ 재직상태
    // ── 급여·신원 (이미지 헤더 기준 확정 필드) ──────────────────────────────
    gender: text('gender'),                 // 성별
    address: text('address'),              // 주소
    residentId: text('residentId'),        // 주민번호 (민감)
    passportNo: text('passportNo'),        // 여권번호
    alienRegNo: text('alienRegNo'),        // 외국인등록번호 (민감)
    bankName: text('bankName'),            // 은행
    bankAccount: text('bankAccount'),      // 계좌번호 (민감, bankBookUrl과 병행)
    accountHolder: text('accountHolder'),  // 예금주
    dailyWage: real('dailyWage'),          // 일당 (개인 단위)
    incomeTax: real('incomeTax'),          // 소득세 공제
    localTax: real('localTax'),            // 주민세 공제
    otherDeduction: real('otherDeduction'), // 기타공제
    createdAt: text('createdAt').default(sql`(CURRENT_TIMESTAMP)`),
    updatedAt: text('updatedAt').default(sql`(CURRENT_TIMESTAMP)`),
}, (table) => ({
    nameIdx: index('worker_name_idx').on(table.name),
    teamIdx: index('worker_team_id_idx').on(table.teamId),
}));

// [방부장] 자재 청구 (MaterialRequest)
export const materialRequests = sqliteTable('MaterialRequest', {
    id: text('id').primaryKey(),
    name: text('name').notNull(),
    spec: text('spec'),
    quantity: real('quantity').default(0),
    unit: text('unit'),
    team: text('team').notNull(),
    date: text('date').notNull(),
    status: text('status').default('청구'),
    memo: text('memo'),
    createdAt: text('createdAt').default(sql`(CURRENT_TIMESTAMP)`),
    updatedAt: text('updatedAt').default(sql`(CURRENT_TIMESTAMP)`),
});

// [방부장] 자재 댓글 (Materi
```

## 연결
- [[홍익인간]]
- [[3지국장_정체성]]
- [[H2OWIND_CLAUDE]]


## 연결

- [[홍익인간]]