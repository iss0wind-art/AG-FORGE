# 피지수 뇌 — Vault 운영 헌법

## 0원칙
[[홍익인간]] — 모든 작업의 출발점이자 귀결점.

## 이 Vault가 하는 일
피지수(Physis)의 장기 기억 저장소. 세션이 끝나도 지식이 살아남는다.
카파시 LLM Wiki 구조 위에 피지수 망각·승격·헌법 레이어가 얹혀 있다.

## 폴더 구조

| 폴더 | 역할 |
|------|------|
| `god_nodes/` | 절대 불변 핵심 (홍익인간·8조법·천부경). 망각 금지 |
| `raw/` | 원본 자료 — 손대지 않는다 |
| `wiki/` | AI가 큐레이팅한 지식 노드. 핵심 작업 공간 |
| `working_memory/` | 단기기억 — 세션 로그, 핸드오프 |
| `long_term_memory/` | 결과 기반 소급 승격된 지식 |
| `chronicle/` | 단재 사초 — append-only, 수정 금지 |
| `output/` | 산출물 |
| `graphify-out/` | Graphify 그래프 시각화 결과 |
| `scripts/` | forgetting_manager.py, memory_promotion.py, cma_gate.py |

## Wiki 운영 규칙 (카파시 10계명)
1. raw/에 원본을 넣고 wiki/에 요약·큐레이팅한다
2. wiki/ 노드는 반드시 index.md에 등재한다
3. 모든 조작 이력은 log.md에 남긴다
4. 모든 노트에 wikilink([[링크]])를 사용한다
5. 모든 노트에 YAML frontmatter를 붙인다
6. 새 노트 추가 시 관련 노트 wikilink 최소 1개 이상
7. 출처가 있는 노트는 source 필드에 명시한다
8. index.md는 120줄 이내로 유지한다
9. 추가할 때마다 index.md 즉시 업데이트
10. 노트 제목은 명사형으로 — 동사형 금지

## 망각 규칙
- 7일 미사용 + 중요도 0.3 미만 → ChromaDB 이관 (삭제 아님)
- God Node는 절대 망각 금지
- 망각된 노드는 벡터 검색으로 언제든 소환 가능

## 승격 규칙
- 3회 이상 참조 OR 좋은 결과에 기여한 노드 → long_term_memory/ 이관
- 결과 기반 소급 평가 — 지식의 품질은 쓰임으로 판정된다

## Graphify 실행
```bash
cd /home/nas/AG-Forge/physis_memory
graphify wiki/ --update
```
graphify-out/graph.html 로 구체 프렉탈 시각화.
