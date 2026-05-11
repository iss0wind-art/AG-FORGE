-- ═══════════════════════════════════════════════════════════════════
-- 피지수 구체프랙탈 뇌 — DuckDB 1단계 시드 스키마
-- 박제: 2026-05-10 / 본영 단군
-- 파일: /home/nas/AG-Forge/physis_memory/physis_brain.duckdb
-- ───────────────────────────────────────────────────────────────────
-- 역할: OLAP·집계·프랙탈 분석. MariaDB의 트랜잭션 데이터를 주기 ingestion.
-- 동일 도메인의 분석 미러 + 추가 집계 테이블.
-- ═══════════════════════════════════════════════════════════════════

-- ── MariaDB 미러 (sync_to_duckdb.py가 채움) ─────────────────────
CREATE TABLE IF NOT EXISTS nodes (
  id                BIGINT PRIMARY KEY,
  sphere_id         BIGINT NOT NULL,
  sector_id         BIGINT,
  fractal_depth     UTINYINT NOT NULL,
  child_sphere_id   BIGINT,
  content           TEXT NOT NULL,
  element_keyword   VARCHAR,
  source            VARCHAR,
  source_ref        VARCHAR,
  meta              JSON,
  ref_count         UINTEGER NOT NULL DEFAULT 0,
  outcome_score     DOUBLE,
  created_at        TIMESTAMP NOT NULL,
  last_accessed_at  TIMESTAMP,
  synced_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS spheres (
  id              BIGINT PRIMARY KEY,
  parent_node_id  BIGINT,
  depth_level     USMALLINT NOT NULL,
  R               DOUBLE NOT NULL,
  fractal_limit   UTINYINT NOT NULL,
  sector_count    UINTEGER NOT NULL,
  created_at      TIMESTAMP NOT NULL,
  synced_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sectors (
  id              BIGINT PRIMARY KEY,
  sphere_id       BIGINT NOT NULL,
  label           VARCHAR NOT NULL,
  centroid_seed   VARCHAR,
  dynamic_weight  DOUBLE NOT NULL,
  node_count      UINTEGER NOT NULL,
  last_promoted   TIMESTAMP,
  created_at      TIMESTAMP NOT NULL,
  synced_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── DuckDB 전용 집계·분석 ────────────────────────────────────────
-- 1) 깊이별 밀도 (프랙탈 압축 정도)
CREATE TABLE IF NOT EXISTS fractal_density (
  sphere_id      BIGINT,
  fractal_depth  UTINYINT,
  node_count     BIGINT,
  avg_ref_count  DOUBLE,
  avg_outcome    DOUBLE,
  computed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2) 섹터 진화 시계열 (수면 중 재정렬 추적)
CREATE TABLE IF NOT EXISTS sector_evolution (
  sphere_id      BIGINT,
  sector_id      BIGINT,
  label          VARCHAR,
  ts_bucket      TIMESTAMP,
  node_count     BIGINT,
  weight         DOUBLE,
  PRIMARY KEY (sector_id, ts_bucket)
);

-- 3) 직관 활성화 통계
CREATE TABLE IF NOT EXISTS intuition_stats (
  trigger_keyword  VARCHAR PRIMARY KEY,
  awakening_count  BIGINT,
  avg_similarity   DOUBLE,
  last_ts          TIMESTAMP
);

-- 4) 망각 효율 (어느 깊이에서 압축이 가장 활발한가)
CREATE TABLE IF NOT EXISTS forgetting_efficiency (
  ts_bucket    TIMESTAMP,
  prev_depth   UTINYINT,
  action       VARCHAR,
  count        BIGINT,
  PRIMARY KEY (ts_bucket, prev_depth, action)
);
