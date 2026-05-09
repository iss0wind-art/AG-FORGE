---
created: 2026-05-09
outcome_score: 0.0
ref_count: 1
tags:
- freecad
- 데이터
- 스키마
- 산출물
type: wiki
---

# FREECAD_DATA_db_schema

> DB 스키마
> 출처: `/home/nas/FreeCAD_4TH/spec/db_schema.sql`
> 흡수일: 2026-05-09

## 구조 요약

```
-- ============================================================
-- FreeCAD_4th DB Schema v2 — Member Manifest 지원
-- Phase 0 산출물 (2026-04-25)
--
-- 적용 대상: SQLite (output/boq.db) + Turso (libsql)
-- 호환성: 기존 boq_jobs 테이블 보존 (절대 DROP 금지)
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- 1. member_specs — 부재 표준 스펙 카탈로그
--    BOQ 프로젝트의 boq_member_specs.json (1,163개) 이식 대상
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS member_specs (
    -- 식별
    symbol          TEXT NOT NULL,           -- "RG1", "TC1", "SL1"
    project_scope   TEXT NOT NULL DEFAULT 'global',
                                              -- 'global' = 모든 프로젝트 공통
                                              -- 또는 특정 project_id

    -- 분류
    member_type     TEXT NOT NULL,           -- BEAM | COLUMN | SLAB | WALL | FOUNDATION
    subtype         TEXT,                    -- edge_beam | transfer_beam | ... (NULL = 일반)

    -- 치수 (mm). 0 = 미사용/배치에서 결정
    width           REAL NOT NULL DEFAULT 0,
    height          REAL NOT NULL DEFAULT 0,
    depth           REAL NOT NULL DEFAULT 0,
    thickness       REAL NOT NULL DEFAULT 0,
    length          REAL NOT NULL DEFAULT 0,
    wall_thickness  REAL NOT NULL DEFAULT 0,

    -- 메타
    remark          TEXT,
    source          TEXT,                    -- 'BOQ_IMPORT' | 'USER' | 'API'
    created_at      TEXT NOT NULL,           -- ISO 8601
    updated_at      TEXT,

    -- 복합 PK: 동일 symbol을 프로젝트별 오버라이드 가능
    PRIMARY KEY (symbol, project_scope),

    CHECK (member_type IN ('BEAM','COLUMN','SLAB','WALL','FOUNDATION')),
    CHECK (width >= 0 AND height >= 0 AND depth >= 0
           AND thickness >= 0 AND length >= 0 AND wall_thickness >= 0)
);

CREATE INDEX IF NOT EXISTS idx_specs_type    ON member_specs(member_type);
CREATE INDEX IF NOT EXISTS idx_specs_scope   ON member_specs(project_scope);
CREATE INDEX IF NOT EXISTS idx_specs_symbol  ON member_specs(symbol);


-- ─────────────────────────────────────────────────────────────
-- 2. projects — 프로젝트 마스터
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    project_id     TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    units          TEXT NOT NULL DEFAULT 'mm',

    -- Manifest 원본 (감사/재현용)
    manifest_yaml  TEXT,
    manifest_hash  TEXT,                     -- SHA256, 변경 감지

    -- 정규화된 컴포넌트 (조회 성능)
    grid_json      TEXT,                     -- {"origin":[0,0], "x_lines":{...}, "y_lines":{...}}
    floors_json    TEXT,                     -- [{"id":"1F","z_base":0,"height":4500}, ...]

    created_at     TEXT NOT NULL,
    updated_at     TEXT,

    CHECK (units IN ('mm','m'))
);


-- ─────────────────────────────────────────────────────────────
-- 3. member_instances — 부재 배치 인스턴스
--    Manifest의 각 멤버를 레코드로 정규화
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS member_instances (
    instance_id    TEXT NOT NULL,            -- 프로젝트 내 유니크
    project_id     TEXT NOT NULL,
    spec_symbol    TEXT NOT NULL,            -- member_specs.symbol 참조
    member_type    TEXT NOT NULL,            -- BEAM|COLUMN|SLAB|WALL|FOUNDATION
    subtype        TEXT,                     -- edge_beam 등 (NULL = 일반)
    floor_id       TEXT NOT NULL,

    -- 배치 정보 (JSON, 4가지 패턴 중 1개)
    -- {"at":{...}} | {"from":{...},"to":{...}} | {"polygon":[...]} | {"vertices_2d":[...]}
    placem
```

## 연결
- [[홍익인간]]
- [[3지국장_정체성]]
- [[FREECAD_CLAUDE]]


## 연결

- [[홍익인간]]