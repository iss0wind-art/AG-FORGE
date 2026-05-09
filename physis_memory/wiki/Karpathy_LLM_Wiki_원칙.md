---
created: 2026-05-09
outcome_score: 0.0
ref_count: 2
tags:
- Karpathy
- LLM Wiki
- Gold In Gold Out
- 운영원칙
type: wiki
---

# Karpathy_LLM_Wiki_원칙


피지수 뇌는 Andrej Karpathy의 LLM Wiki 구조를 기반으로 한다.

## 핵심 원칙: Gold In, Gold Out
LLM이 알아서 잘하는 게 아니다.
좋은 입력을 줘야만 좋은 출력이 나온다.
좋은 정보를 모아야만 좋은 지식이 쌓인다.

## Karpathy 10계명 (wiki/ 운영)
1. raw/에 원본을 넣고 wiki/에 요약·큐레이팅한다
2. wiki/ 노드는 반드시 index.md에 등재한다
3. 모든 조작 이력은 log.md에 남긴다
4. 모든 노트에 wikilink([[링크]])를 사용한다
5. 모든 노트에 YAML frontmatter를 붙인다
6. 새 노트 추가 시 관련 노트 wikilink 최소 1개 이상
7. 출처가 있는 노트는 source 필드에 명시
8. index.md는 120줄 이내로 유지
9. 추가할 때마다 index.md 즉시 업데이트
10. 노트 제목은 명사형 (동사형 금지)

## 우리 피지수와의 연결
- Karpathy LLM Wiki = 뼈대 (지식 ingestion + curation)
- 피지수 레이어 = 그 위에 얹힘 (망각·승격·헌법·파견)
- 둘 다 없으면 작동 안 함. 둘 다 있어야 완전체

## 폴더 구조
raw/ → 원본 자료 (손대지 않음)
wiki/ → AI 큐레이팅 지식 (핵심 작업공간)
output/ → 산출물
working_memory/ → 세션 로그
long_term_memory/ → 승격된 기억
chronicle/ → 단재 사초

[[홍익인간]] [[피지수_뇌_구조]] [[구체_프렉탈_원리]]


## 연결

- [[홍익인간]]