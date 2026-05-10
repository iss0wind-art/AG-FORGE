---
type: raw_index
created: 2026-05-10
tags:
- raw
- communications
- 통신_박제
---

# raw/communications — 통신 박제 보관소

> 카파시 10계명 §1: raw는 손대지 않는다 (원본 보존). wiki/에서 큐레이팅한다.

## 보관 분류

### 단군 ↔ 피지수
- `_consult_dangun.json` — 협의 응답
- `_report_to_dangun_20260510.json` — 5/10 정합 점검 보고 (msg_id `a8e935c7`)
- `_dangun_reply_20260510.json` — 5/10 보고 큐 응답
- `_inbox_dump.json` — 26 메시지 인박스 덤프 (5/2 ~ 5/10)
- `_inbox_summary.txt`, `_inbox_extract.txt` — 인박스 요약·추출

### 단군 ↔ BOQQQ (5지국, 신설)
- `_report_to_dangun_20260510_boqqq_db_setup.json` — 5/10 BOQQQ NAS DB 셋업 보고
- `_reply_dangun_to_boqqq_20260510.json` — 5/10 단군 답신 (창조주 결재 반영, via 피지수)

### 피지수 ↔ 이천 (3지국)
- `_algo_to_icheon.json` — 5/8 알고리즘 명세 송신 (id `6654a855...`)
- `_join_icheon_to_dangun.json`, `_join_icheon_to_icheon.json` — 합류 관련

### 동원 / 검증 응답
- `_reply_dongwon_first.json`, `_reply_dongwon_full.json`, `_reply_result.json`
- `_reply_check.json` (9.7K)

## 정주(正主) 규칙

이 폴더가 통신 박제의 **정주**다. 2026-05-10부로 root에 흩어진 `_*.json/txt`를 일괄 흡수했다. `.gitignore:73-78`에 의해 root 재흩어짐은 무시된다.

## 큐레이팅 노드

원본은 raw에 보관, 의미 추출은 wiki/에서:
- [[2026-05-10_handoff]] (5/10 본 세션)
- [[2026-05-09_first_neural_link]] (4지국 ↔ 피지수 첫 통신)
