-- ═══════════════════════════════════════════════════════════════════
-- 피지수 구체프랙탈 뇌 — MariaDB 1단계 시드 스키마
-- 박제: 2026-05-10 / 본영 단군 (창조주 결재)
-- 원본 설계: PHYSIS_BRAIN_FRACTAL_SPHERE_2026-05-04.md
-- DB: physis_brain (utf8mb4)
-- ───────────────────────────────────────────────────────────────────
-- 역할: 관계형·트랜잭션 측면. 노드/구체/섹터 정합성 보장.
-- DuckDB 측은 동일 데이터의 OLAP·집계·프랙탈 분석.
-- 임포트 파이프: MariaDB → DuckDB (sync_to_duckdb.py)
-- ═══════════════════════════════════════════════════════════════════

USE physis_brain;

-- ── 구체(Sphere) ────────────────────────────────────────────────
-- 멀티버스 재귀: 데이터 노드 하나가 또 다른 구체를 가리킬 수 있음
-- (parent_node_id로 역참조). 1단계는 재귀 없는 단일 구체로 시작.
CREATE TABLE IF NOT EXISTS spheres (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  parent_node_id  BIGINT UNSIGNED NULL,            -- 멀티버스 재귀: 어느 노드가 이 구체를 품었나
  depth_level     SMALLINT UNSIGNED NOT NULL DEFAULT 0,  -- 무한 재귀의 깊이 (0=최외곽)
  R               DOUBLE NOT NULL DEFAULT 1.0,     -- 균등 거리 (천부경: 一始無始一)
  fractal_limit   TINYINT UNSIGNED NOT NULL DEFAULT 5,  -- 표면 프랙탈 단계 제한 (3~5)
  sector_count    INT UNSIGNED NOT NULL DEFAULT 0,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_spheres_parent (parent_node_id),
  KEY idx_spheres_depth (depth_level)
) ENGINE=InnoDB COLLATE=utf8mb4_unicode_ci;

-- ── 섹터(Sector) — 동적 클러스터 ─────────────────────────────────
-- 처음엔 랜덤. 인과관계로 자동 클러스터링. 경계는 항상 변함.
CREATE TABLE IF NOT EXISTS sectors (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  sphere_id       BIGINT UNSIGNED NOT NULL,
  label           VARCHAR(255) NOT NULL,           -- "동물", "식물", "주식", "감성" 등
  centroid_seed   VARCHAR(512) NULL,               -- 섹터 중심 단어 (피지수가 자율 결정)
  dynamic_weight  DOUBLE NOT NULL DEFAULT 1.0,     -- 섹터 활성 가중치 (수면 중 재정렬)
  node_count      INT UNSIGNED NOT NULL DEFAULT 0,
  last_promoted   TIMESTAMP NULL,                  -- 마지막 승격 사건 (sweep-A/B)
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_sectors_sphere FOREIGN KEY (sphere_id) REFERENCES spheres(id) ON DELETE CASCADE,
  KEY idx_sectors_label (label)
) ENGINE=InnoDB COLLATE=utf8mb4_unicode_ci;

-- ── 노드(Node) — 구체 표면의 데이터 점 ────────────────────────────
-- 모든 노드는 중심에서 거리 R 동일 (구조적 보장).
-- 깊이가 fractal_limit에 도달하면 망각으로 넘어가고 원소 단어만 1단계에 잔존.
CREATE TABLE IF NOT EXISTS nodes (
  id                BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  sphere_id         BIGINT UNSIGNED NOT NULL,
  sector_id         BIGINT UNSIGNED NULL,           -- 섹터 미배정 가능 (랜덤 단계)
  fractal_depth     TINYINT UNSIGNED NOT NULL DEFAULT 1,  -- 1=원소 단어, 깊이 ↑
  child_sphere_id   BIGINT UNSIGNED NULL,           -- 멀티버스 재귀: 이 점이 또 다른 구체
  content           TEXT NOT NULL,                  -- 데이터 본문
  element_keyword   VARCHAR(255) NULL,              -- 망각 후 잔존할 원소 단어
  source            VARCHAR(64) NULL,               -- "stock_jiguk", "freecad_jiguk", "user_dialogue" 등
  source_ref        VARCHAR(255) NULL,              -- 원본 식별자 (4지국 종목코드, 사건 ID 등)
  meta              JSON NULL,                      -- 자유 메타 (피지수 자율)
  ref_count         INT UNSIGNED NOT NULL DEFAULT 0,    -- 참조 횟수 (소급 평가)
  outcome_score     DOUBLE NULL,                    -- 사후 결과 점수
  created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_accessed_at  TIMESTAMP NULL,
  CONSTRAINT fk_nodes_sphere FOREIGN KEY (sphere_id) REFERENCES spheres(id) ON DELETE CASCADE,
  CONSTRAINT fk_nodes_sector FOREIGN KEY (sector_id) REFERENCES sectors(id) ON DELETE SET NULL,
  KEY idx_nodes_depth (fractal_depth),
  KEY idx_nodes_source (source, source_ref),
  KEY idx_nodes_element (element_keyword),
  FULLTEXT KEY ft_nodes_content (content)
) ENGINE=InnoDB COLLATE=utf8mb4_unicode_ci;

-- ── 망각 로그(Forgetting) — sweep-A 산물 ─────────────────────────
CREATE TABLE IF NOT EXISTS forgetting_log (
  id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  node_id     BIGINT UNSIGNED NOT NULL,
  prev_depth  TINYINT UNSIGNED NOT NULL,
  action      ENUM('promote_to_element','demote','prune','merge') NOT NULL,
  reason      VARCHAR(512) NULL,
  ts          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_forgetting_node (node_id),
  KEY idx_forgetting_ts (ts)
) ENGINE=InnoDB COLLATE=utf8mb4_unicode_ci;

-- ── 직관·데자뷰(Intuition) — 원소 단어 → 깊은 기억 활성화 ───────
CREATE TABLE IF NOT EXISTS intuitions (
  id                  BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  trigger_node_id     BIGINT UNSIGNED NOT NULL,    -- 1단계 원소 단어 노드
  awakened_node_id    BIGINT UNSIGNED NOT NULL,    -- 깊은 단계에서 깨어난 노드
  similarity          DOUBLE NULL,
  awakened_depth      TINYINT UNSIGNED NULL,
  ts                  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_intuitions_trigger (trigger_node_id),
  KEY idx_intuitions_ts (ts)
) ENGINE=InnoDB COLLATE=utf8mb4_unicode_ci;

-- ── 메타 운영 ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS physis_meta (
  k           VARCHAR(64) PRIMARY KEY,
  v           TEXT NOT NULL,
  updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COLLATE=utf8mb4_unicode_ci;

-- 시드 메타
INSERT IGNORE INTO physis_meta (k, v) VALUES
  ('schema_version',     '1'),
  ('seeded_by',          'dangun_2026-05-10'),
  ('design_origin',      'PHYSIS_BRAIN_FRACTAL_SPHERE_2026-05-04.md'),
  ('天符經',             '一始無始一 析三極無盡本'),
  ('R_default',          '1.0'),
  ('fractal_limit',      '5'),
  ('next_step_owner',    'physis_self_evolution');

-- 최외곽 구체 1개 시드 (피지수의 첫 구체)
INSERT IGNORE INTO spheres (id, depth_level, R, fractal_limit) VALUES (1, 0, 1.0, 5);
