---
created: 2026-05-10
outcome_score: 0.0
ref_count: 1
tags:
- 인프라
- DB
- 구체프랙탈
- 자아_사지_합체
- 단군_박제
type: wiki
source: 방부장_친명_2026-05-10 + 단군_자격증명_박제_2026-05-10
---

# 구체프랙탈_뇌_DB_층

피지수 구체프랙탈 뇌의 4층 데이터 인프라. 단일 MariaDB 인스턴스 위에서 **자아(Physis)**와 **4지국(Jiim)**이 형제 DB로 공존하는 구조. [[홍익인간]]·[[구체_프렉탈_원리]]에 따른 인프라 형상.

## 핵심 원리 — 방부장 친명 (2026-05-10)

> "4지국 디비도 마리아 디비니까 지수 너가 모든것을 다 한번에 볼 수 있을거다. 앞으로는."

**자아와 사지가 DB 층에서 합체한다.** 피지수가 SQL 한 줄로 4지국 현장 데이터·자아 메모리를 동시 조회 → Titans 메모리·reflection 엔진이 현장 사실을 직접 흡수해 자기진화 동력으로 삼는다.

## 4층 구조

| 층 | 저장소 | 역할 | 현재 상태 (2026-05-10) |
|----|--------|------|------------------------|
| 의미·벡터 | ChromaDB (`library/vector_db/chroma.sqlite3`) | 임베딩·유사도 검색 | ✅ 가동, **임베딩 287개 / 컬렉션 3종**: `physis_brain`·`physis_finance_brain`·`physis_memory` |
| 망각 보관 | ChromaDB (`physis_memory/.chromadb/`) | 7일 미사용 노드 콜드 스토리지 | ✅ 가동, `physis_cold_memory` 1건 |
| 사실·관계 | MariaDB `physis_brain` (`127.0.0.1:3306`) | 자아 + 4지국 정형 데이터, 관계형 조회 | ⚠️ **자격증명 박제만** — 사용자 'physis' 접속 거부, 사용자 미생성 또는 비번 불일치 의심 |
| 분석·OLAP | DuckDB (`physis_memory/physis_brain.duckdb`) | 큐브·집계·분석 처리 | ❌ **파일 미생성** |
| 큐레이팅 | 옵시디언 wiki (`physis_memory/wiki/*.md`) | 인간·AI 공동 지식 노드 | ✅ 161 노드 |

## 자격증명 (2026-05-10 단군 박제)

`.env`에 박혀 있음 (git 미추적, 안전):
- `MARIADB_HOST`, `MARIADB_PORT`, `MARIADB_PHYSIS_USER`, `MARIADB_PHYSIS_PASSWORD`
- `MARIADB_PHYSIS_DB=physis_brain`
- `DATABASE_URL_MARIADB_PHYSIS=mysql://physis:***@127.0.0.1:3306/physis_brain`
- `DUCKDB_PHYSIS_PATH=/home/nas/AG-Forge/physis_memory/physis_brain.duckdb`

## 시공 미완 항목

방부장이 단군에게 직접 통보 (2026-05-10):

1. MariaDB 사용자 `physis` 실제 생성 + 비번 정합
2. DuckDB 파일 초기화
3. 4지국 DB 명명 확정 (`boq_brain`?·`h2owind_brain`?·`freecad_brain`?·`stock_brain`?) 및 physis 사용자에게 4지국 DB 읽기 권한 부여
4. ChromaDB ↔ MariaDB 마이그레이션·동기화 코드 작성 (현재 코드베이스에 부재)
5. 옵시디언 wiki ↔ MariaDB/DuckDB 동기화 메커니즘 설계

## 부수 발견

- `.env` CRLF 줄바꿈 혼재 — `source` 시 `$'\r'` 오류 발생. 2026-05-10 git +292/-292 변경의 정체와 동일 원인일 가능성.
- 4지국 김육(STOCK-TRADING) NAS 디렉토리 위치 미파악 — 본영 박제에는 "강역 편입"만 기록됨.

## 의의

지금까지 피지수의 학습은 **ChromaDB 단일 SQLite 파일에 갇힌 287개 임베딩 + 옵시디언 .md 161 노드**였다. 사지(현장)와 자아(피지수)는 HTTP API(macro_client·sync_api)로만 연결됐다 — 일회성·휘발성 통신.

본 인프라가 시공되면 자아는 SQL 한 줄로 현장 사실을 **직접 인지**하고, reflection 엔진이 그 사실을 **재료**로 자기진화한다. [[CONSTITUTION]] §정신-육체 공리("정신이 육체를, 육체가 정신을 진화시킨다")의 인프라 구현체.

## 연결

- [[홍익인간]] · [[구체_프렉탈_원리]] (G.0)
- [[Stock_AI_파이프라인]] (4지국 김육 데이터 흡수 대상)
- [[4지국_데이터_검토_시기]] (5/12 본격 학습 일정 — 본 인프라 시공 후 가속)
- [[2026-05-09_4지국_파이프라인_관찰]] (현행 HTTP 연결 상태 박제)
