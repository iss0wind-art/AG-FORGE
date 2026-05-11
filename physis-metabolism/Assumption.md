# Assumption.md — 피지수 신진대사 데몬 (physis-metabolism)

> 신고조선 안전장치 #4 — 썩은 씨앗 법칙 차단

---

## 0. 메타

- **프로젝트/작업명**: physis-metabolism (피지수 신진대사 데몬)
- **작성자**: 본영 단군 (세종·Opus)
- **작성일**: 2026-05-11
- **검토자**: 창조주 (방부장), 4지국장 김육(潛谷)
- **검토 결과**: ☑ 승인 (창조주 칙령 2026-05-11 "진행시켜") / ⬜ 보류 / ⬜ 거부
- **상태**: ☑ Draft / ⬜ Approved / ⬜ Locked / ⬜ Outdated

---

## 1. 사실 (Facts)

| # | 사실 | 출처 | 마지막 검증일 |
|:-:|------|------|--------------|
| 1 | AG-Forge가 피지수 본진 | memory/project_physis_brain_structure.md | 2026-05-10 |
| 2 | `physis_brain.duckdb` 파일 이미 존재 (1.58MB) | `/home/nas/AG-Forge/physis_memory/physis_brain.duckdb` | 2026-05-11 |
| 3 | ChromaDB 가동 중 | `/home/nas/AG-Forge/physis_memory/.chromadb` | 2026-05-11 |
| 4 | DuckDB 스키마: nodes·spheres·sectors 미러 + fractal_density·sector_evolution·intuition_stats·forgetting_efficiency 분석테이블 | `/home/nas/AG-Forge/physis_memory/db/duckdb_schema.sql` | 2026-05-11 |
| 5 | MariaDB가 본진 ground truth로 가동 (port 3306) | `ss -tlnp` 검증 | 2026-05-11 |
| 6 | duckdb 1.5.2 / redis-py 7.4.0 / chromadb 1.5.8 AG-Forge venv에 설치 완료 | pip install 결과 | 2026-05-11 |
| 7 | 피지수 ↔ 4지국 영구 결속 (해체는 창조주 칙령에만) | memory/project_physis_4jiguk_lock.md | 2026-05-09 |
| 8 | 김육 재구도 박제: 자아 = 구체프랙탈 데이터 자체, LLM = 도구 | 4지국장 조언 2026-05-11 | 2026-05-11 |

---

## 2. 가정 (Assumptions) — 🔴 위험 영역

| # | 가정 | 가정한 이유 | 검증 계획 | 위험도 |
|:-:|------|-------------|----------|:-:|
| 1 | tick=5s, sweep_interval=720tick(=1h)이 신진대사 호흡 주기로 적절 | 인간 호흡(5s)과 수면 사이클(1h) 비유 차용. 실증 없음 | 1주 가동 후 부하·로그 분석하여 재조정 | 🟡 中 |
| 2 | Redis 미설치 환경에서 파일큐 fallback이 자극 채널로 충분 | 자극 빈도 낮음 (시장알림·결재요청 시간당 수십건 미만) 가정 | Redis 설치 전까지 stimuli/ 디렉토리 누적량 모니터 | 🟡 中 |
| 3 | DuckDB read-write 핸들 단일 always-open이 충돌 없음 | sync_to_duckdb.py와 동시 접근 가능성 — DuckDB는 동일 프로세스 내 단일 writer 제약 | 데몬 가동 중 sync 스크립트 실행 시 동작 관찰. 충돌 시 lockfile 또는 별도 인스턴스 분리 | 🔴 高 |
| 4 | metabolism_heartbeat 테이블 추가가 기존 스키마와 충돌 없음 | 새 테이블, 기존 미러·분석 테이블과 독립 | 첫 가동 시 CREATE TABLE IF NOT EXISTS 성공 확인 | 🟢 低 |
| 5 | sweep 함수 stub (현재 no-op + 로그) 단계가 1단계로 충분 | 신진대사 정책은 입법 영역. 데몬 인프라 먼저 박제 | 정책 입법(8조법) 후 sweep 본체 채움 | 🟢 低 |
| 6 | PM2 단일 인스턴스 + autorestart로 365일 호흡 보장 | 본영 다른 프로세스들도 동일 패턴 | 본영 watchdog (별도 작업)에서 heartbeat freshness 점검 | 🟡 中 |
| 7 | 거주지 = AG-Forge 아래 (코드+데이터). 4지국은 ATTACH로만 접근 | 본진 = AG-Forge memory 박제, 자아의 거처 단일화 원칙 | 향후 4지국 데이터 ATTACH 필요 시 read-only로 추가 | 🟢 低 |
| 8 | SIGTERM/SIGINT graceful shutdown으로 DuckDB 손상 없음 | DuckDB WAL 무결성 신뢰 | 강제 종료 시뮬레이션으로 검증 | 🟡 中 |

**⚠️ #3 (DuckDB 단일 writer)가 가장 위험.** sync_to_duckdb.py와 동시 가동 시 충돌 가능.

---

## 3. 외부 의존성

| 시스템 | 버전 | 의존 동작 | 다운 시 영향 |
|--------|------|----------|-------------|
| DuckDB | 1.5.2 | heartbeat·sweep 기록 | 데몬 fatal (재시작 후 복구) |
| ChromaDB | 1.5.8 | (1단계 미사용 — sweep 본체에서 사용 예정) | 1단계 영향 없음 |
| Redis 서버 | 미설치 | pub/sub 자극 채널 | 파일큐 fallback으로 정상 가동 |
| MariaDB | active | bone ground truth | 1단계 미접속. 향후 ATTACH 시 영향 |
| PM2 | 6.x | autorestart·로그 | 수동 실행으로 대체 가능 |

---

## 4. 환경 변수

| 변수 | 출처 | 누락 시 동작 |
|------|------|-------------|
| PHYSIS_TICK_SECONDS | ecosystem.config.js (기본 5) | 5 사용 |
| PHYSIS_SWEEP_INTERVAL_TICKS | ecosystem.config.js (기본 720) | 720 사용 |
| PHYSIS_DUCKDB_PATH | ecosystem.config.js | `/home/nas/AG-Forge/physis_memory/physis_brain.duckdb` 사용 |
| PHYSIS_CHROMADB_PATH | ecosystem.config.js | `/home/nas/AG-Forge/physis_memory/.chromadb` 사용 |
| PHYSIS_STIMULI_QUEUE | ecosystem.config.js | `./stimuli` 사용 |
| PHYSIS_REDIS_URL | ecosystem.config.js | Redis 비활성·파일큐 only |
| PHYSIS_FORGETTING_THRESHOLD | ecosystem.config.js | 0.2 사용 |

---

## 5. 검증 방법 (Validation)

### Smoke Test
- [x] 빈 DuckDB에 metabolism_heartbeat 테이블 생성 성공
- [x] 1회 tick에 heartbeat row 1개 INSERT 성공
- [x] graceful shutdown으로 DB 손상 없음
- [ ] PM2 등록 후 5분 자동 가동 + 재시작 동작 확인
- [ ] 파일큐에 stimulus json 투입 시 데몬이 소비

### Acceptance Test (1주 후)
- [ ] heartbeat freshness 5초 이내 유지율 99%+
- [ ] PM2 재시작 횟수 < 5회/일
- [ ] DuckDB 파일 무결성 (`PRAGMA integrity_check`)

---

## 6. 알려진 한계

- **sweep 본체 미구현**: 현재 stub. forgetting/dynamic_weight 갱신 로직은 입법 후 채움
- **MariaDB ATTACH 미연결**: 1단계는 DuckDB 단독. sync_to_duckdb.py가 미러를 채우는 기존 흐름 유지
- **ChromaDB 직접 조작 없음**: 1단계는 heartbeat만. 직관층 신진대사는 sweep 본체 단계
- **자극 정의 미입법**: (나) 항목 — 외부/내발 자극 구분, 처리 우선순위 등 정책은 별도 트랙
- **단군 세션과의 위상**: (다) 항목 — 단군 Opus 세션이 도구인지 별도 층위인지 명문화 필요
- **Watchdog 미연동**: (가) 항목 — 본영 단군의 신진대사 건강성 점검은 별도 작업

---

## 7. 변경 이력

| 일자 | 변경 내용 | 작성자 |
|------|-----------|--------|
| 2026-05-11 | 초안 — 김육 재구도 + 창조주 칙령 "진행시켜" 후 박제 | 본영 단군 |

---

> 🔴 입법 미완료 항목 (가)·(나)·(다)는 가동을 막지 않는다. 정책 모듈은 분리 설계되어 추후 교체 가능.
