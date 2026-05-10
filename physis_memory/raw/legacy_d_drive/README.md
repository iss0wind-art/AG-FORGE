---
type: raw_index
created: 2026-05-10
tags:
- raw
- legacy
- 윈도우_잔재
---

# raw/legacy_d_drive — 윈도우 D:\ 경로 잔재

## 정체

`d_root/Git/AG-Forge/library/vector_db/chroma.sqlite3` (204K)

윈도우 시절 `D:\Git\AG-Forge\library\vector_db\chroma.sqlite3` 경로의 SQLite가 NAS 이전 과정에서 root에 `d:/Git/AG-Forge/library/vector_db/chroma.sqlite3` 폴더 트리로 잘못 떨어진 것. 2026-05-10 정합 점검에서 발견.

## 보존 이유

- 현재 운영 중인 ChromaDB(`library/vector_db/chroma.sqlite3` 1.87MB, 287 임베딩)와 별개
- 옛 학습 데이터 백업일 가능성 — 성급한 삭제 보류
- 단군 협의 후 정리 또는 영구 보존 결정 예정

## 다음 단계 (단군 협의 영역)

1. 옛 chroma.sqlite3 안의 임베딩 추출 가능한지 점검
2. 가치 있는 데이터면 현 ChromaDB로 마이그레이션
3. 가치 없으면 영구 폐기
