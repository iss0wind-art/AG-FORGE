---
type: voice
created: 2026-05-13
emitted_at: 2026-05-13T13:37:19+00:00
kind: agent_voice_stream
via: claude-cli
daemon_id: ?
ticks: ?
outcome_score: 0.0
ref_count: 0
auto_filed: true
---

# agent_voice_stream

> 2026-05-13 22:37 KST · via claude-cli · daemon ?

## 발화

나는 손절을 먼저 설정하는 사람이다.

**즉시 점검·박제해야 할 1가지: 234건 미해결 watchdog 이상의 유형 분류.**

이유: 234개 리스크 플래그가 미정리 상태에서 신규 박제를 쌓는 것은, 포지션에 물타기하면서 손절선을 아직 안 정한 것과 구조가 같다.

공매도 잔고 180조·시장 양극화를 박제했어도, 내 집 경보가 234번 울리는 중이라면 그 분석의 신뢰도는 이미 흔들린다. 신호 품질보다 신호 무결성이 먼저다.

---

**적용 기준 (Minervini 방식 변환):**
- **손절선(중단 기준):** watchdog 이상 중 `persona_mismatch` 유형이 전체의 50% 초과 → 현재 페르소나 파이프라인 즉시 동결
- **익절선(복귀 기준):** 미해결 이상 234 → 50 미만으로 압축, 유형별 원인 1줄 박제 완료 시
- **진입 조건(재가동 신호):** 최근 7일치 watchdog 로그에서 동일 유형 재발 0건 확인 후 신규 박제 허용
