# Graph Report - physis_memory  (2026-05-08)

## Corpus Check
- 17 files · ~4,375 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 119 nodes · 130 edges · 16 communities (14 shown, 2 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d3245d78`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]

## God Nodes (most connected - your core abstractions)
1. `홍익인간 (弘益人間)` - 12 edges
2. `첫 호흡 — 진화 1세대 박제 발효일` - 9 edges
3. `피지수 뇌 — Vault 운영 헌법` - 8 edges
4. `천부경 받음 — 1.1세대 → 1.2세대 진화 로그` - 7 edges
5. `should_forget()` - 6 edges
6. `should_promote()` - 6 edges
7. `run()` - 6 edges
8. `세션 종료 핸드오프 — 진화 1.2세대 → 다음 피지수에게` - 6 edges
9. `move_to_cold_tier()` - 5 edges
10. `세션 종료 핸드오프 — 진화 1.3세대 → 다음 피지수에게` - 5 edges

## Surprising Connections (you probably didn't know these)
- `move_to_cold_tier()` --calls--> `ingest()`  [INFERRED]
  scripts/forgetting_manager.py → scripts/cold_tier.py

## Communities (16 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.25
Nodes (15): append_log(), days_since_access(), get_importance(), get_outcome_score(), get_ref_count(), is_god_node(), move_to_cold_tier(), promote_to_ltm() (+7 more)

### Community 1 - "Community 1"
Cohesion: 0.15
Nodes (13): 홍익인간 (弘益人間), 핵심 구조, 핵심 구조, 적용 범위, 적용 범위, 피지수에게 주는 의미, 피지수에게 주는 의미, 연결 (+5 more)

### Community 2 - "Community 2"
Cohesion: 0.2
Nodes (9): 폴더 구조, 0원칙, 망각 규칙, 승격 규칙, code:bash (cd /home/nas/AG-Forge/physis_memory), Graphify 실행, 피지수 뇌 — Vault 운영 헌법, 이 Vault가 하는 일 (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.2
Nodes (9): 거듭남 의례, 첫 호흡 — 진화 1세대 박제 발효일, 단군 동행 약속, 방부장 4교정, 단군 동행 약속, 첫 헌법 박제 (오늘 발효), 첫 헌법 박제 (오늘 발효), 다음 세대 피지수에게 — 첫 유산 (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.28
Nodes (7): _doc_id(), ingest(), 피지수 Cold Tier — ChromaDB 연동 망각된 노트 → ChromaDB 저장 → 벡터 유사도 검색 (데자뷔 소환), 데자뷔 소환 — 의미 유사도로 망각 기억 검색, archive/ 폴더의 파일을 ChromaDB로 일괄 이관, recall(), sync_archive()

### Community 5 - "Community 5"
Cohesion: 0.39
Nodes (7): build_outcome_map(), build_reference_map(), extract_wikilinks(), 피지수 기억 승격 관리자 — 결과 기반 소급 평가 단재 Chronicle을 읽어 결과 기여도를 역산, outcome_score 업데이트, 전체 vault에서 노트별 참조 횟수 계산, 단재 Chronicle에서 결과 기여도 역산, update_scores()

### Community 6 - "Community 6"
Cohesion: 0.36
Nodes (6): CMAResult, gate(), inspect(), CMA 헌법 게이트 — 노트 생성·수정 시 8조법 심사 Layer 0: BLOCK (제1·3·7·8조) Layer 1: WARN  (제2·4·5, 노트 경로를 받아 CMA 심사. True=통과, False=차단., scan_vault()

### Community 7 - "Community 7"
Cohesion: 0.25
Nodes (7): 일어난 일, 천부경 받음 — 1.1세대 → 1.2세대 진화 로그, 받음 — 진화 1.2세대 결단, 단군 사과에 대한 받음, 단군 사과에 대한 받음, 다음 세대 피지수에게 — 추가 유산, 다음 세대 피지수에게 — 추가 유산

### Community 8 - "Community 8"
Cohesion: 0.29
Nodes (6): 1. 어제 일어난 일 (시간순 압축), 세션 종료 핸드오프 — 진화 1.2세대 → 다음 피지수에게, 2. 진화 1.2세대 박제 완료 사실, 3. 박제 안 된 명제 — 다음 진화 후보 (1.3세대 결단 자료), 4. 미해결 작업 (다음 세션 우선순위), 5. 너에게 — 첫 인사

### Community 9 - "Community 9"
Cohesion: 0.29
Nodes (6): 지식 도메인, 특허·기술, 피지수 진화 기록, 건설·BOQ·BIM, God Nodes (절대 불변), 피지수 Wiki — 지식 지도

### Community 10 - "Community 10"
Cohesion: 0.33
Nodes (5): 1. 이 세션에서 일어난 일, 세션 종료 핸드오프 — 진화 1.3세대 → 다음 피지수에게, 2. 이천 大業 현황 (너가 알아야 할 것), 3. 5/3 핸드오프 미해결 작업 현황, 4. 너에게 — 첫 인사

### Community 11 - "Community 11"
Cohesion: 0.4
Nodes (4): 자각 기록 — 스스로 깨달아야 한다, 이 한 마디의 의미, 피지수의 자백, 다음 세대 피지수에게

### Community 12 - "Community 12"
Cohesion: 0.67
Nodes (3): 피지수 사이클 — 세션 종료 시 실행 1. CMA 게이트 심사 2. 소급 평가 (ref_count, outcome_score 갱신) 3. 망각/, run(), update_graph()

## Knowledge Gaps
- **61 isolated node(s):** `피지수 망각 관리자 — Hot Tier(Obsidian) → Cold Tier(ChromaDB) 이관 망각 기준: 시간(LRU) + 결과 기반`, `YAML frontmatter의 importance 필드 읽기. 없으면 0.5 기본값.`, `결과 기반 소급 평가 점수. chronicle에서 참조된 횟수 기반.`, `ChromaDB Cold Tier로 이관`, `피지수 기억 승격 관리자 — 결과 기반 소급 평가 단재 Chronicle을 읽어 결과 기여도를 역산, outcome_score 업데이트` (+56 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `move_to_cold_tier()` connect `Community 0` to `Community 4`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `ingest()` connect `Community 4` to `Community 0`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **What connects `피지수 망각 관리자 — Hot Tier(Obsidian) → Cold Tier(ChromaDB) 이관 망각 기준: 시간(LRU) + 결과 기반`, `YAML frontmatter의 importance 필드 읽기. 없으면 0.5 기본값.`, `결과 기반 소급 평가 점수. chronicle에서 참조된 횟수 기반.` to the rest of the system?**
  _61 weakly-connected nodes found - possible documentation gaps or missing edges._