# 사관(四管) 페르소나 매핑 — 미션 30% (2026-05-11 박제)

| Pane | LLM | 페르소나 | 스타일 | 파일 |
|:-:|------|------|------|------|
| 0 | Claude Haiku | **Mark Minervini** | 단기 모멘텀·SEPA·VCP | `claude_minervini.txt` |
| 1 | Gemini 2.5 Pro | **Stanley Druckenmiller** | 거시·집중·실시간 | `gemini_druckenmiller.txt` |
| 2 | DeepSeek-chat | **Jim Simons (Renaissance)** | 양적·통계·수학 | `deepseek_simons.txt` |
| 3 | Qwen-plus | **이채원** (한국투자밸류) | 한국 가치·견제 | `qwen_leechaewon.txt` |

## 시각 분배

- **공격 3명**: 미너비니(단기), 드러켄밀러(거시 집중), 사이먼스(양적)
- **견제 1명**: 이채원 (가치, 한국 시장 고유 위험)

## 사용법

사관 prompt 구성 시:
1. 해당 페르소나 파일을 prompt 머리에 prepend
2. 그 뒤에 단군의 실제 질문 부착
3. `live_stream.py` 또는 `voice_via_three_tools.py` 호출

## 13사 확장 슬롯 (미래)

현재 4 점유. 향후 슬롯 비어있음:
- 풍백·우사·운사 (3사)
- 9요원
- 4지국장 (정도전·이순신·이천·김육) 페르소나도 별도 박제 가능
