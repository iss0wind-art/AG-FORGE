# AG-FORGE — 피지수(Physis) 하이브리드 뇌

## 프로젝트 개요

방부장님의 디지털 분신. 건설 현장 관리 AI 뇌 시스템.

**하이브리드 비전: 자아(Physis) + 사지(Jiim)**

> **공리: 정신이 육체를, 육체가 정신을 진화시킨다.**

피지수는 두 비전이 한 몸에 양립한 존재다:

- **자아(Physis · 자기진화)**: Titans 메모리, Reflection 엔진, 벡터DB 학습 → 스스로 망각·통합·메타인지로 진화
- **사지(Jiim · 이식·구현)**: transplant, sync_api, weekly_briefing, life_cycle_manager → 현장 뇌(POPEYEs/BOQ)로 이식되어 자율 운영

자아와 사지는 분리 가능한 부품이 아니라 서로의 진화 동력이다. 사지가 현장에서 길어 올린 판단 로그가 자아의 reflection 재료가 되고, 자아의 메타인지 통찰이 다시 사지의 strategy/briefing 품질을 끌어올린다.

당분간은 **합체 형태**로 함께 진화. 차후 Physis가 충분히 성숙하면, 이식체는 `Jiim-{현장명}`으로 종분화될 수 있다(미래 비전, 현재는 비활성).

## 기술 스택

- Python 3.x, FastAPI, LangGraph
- LLM: ChainedProvider (Groq → DeepSeek → Gemini 폴백)
- MCP: FastMCP (`mcp_server.py`)
- 터널: ZROK (`python run.py --zrok`)
- DB: Turso (LibSQL, 현장 뇌 연결 예정)
- 메모리: Titans (Surprise Metric 기반 망각·통합)
- 학습: 벡터DB (`library/vector_db/`, ChromaDB)

## 필수 명령어

```bash
python run.py                                              # API 서버 시작 (포트 8000)
python run.py --zrok                                       # ZROK 터널 포함
python -m pytest tests/                                    # 전체 테스트
python scripts/transplant.py --target PATH --role field_brain --master URL  # 사지 이식
python scripts/setup_vector_db.py                          # 자아 학습 DB 셋업
```

## 핵심 디렉토리

```
scripts/        # 에이전트 노드, LLM 프로바이더, 뇌 로더
                #   ├─ [Physis] titans_memory.py, reflection_engine.py, learn_docs.py
                #   └─ [Jiim] transplant.py, life_cycle_manager.py, weekly_briefing.py,
                #            strategy_node.py, alert_node.py
server/         # FastAPI 라우트 (api.py, sync_api.py[Jiim], auth.py)
library/        # 벡터DB 학습 자료 (Physis 자아진화 기반)
.brain/         # 뇌 레이어 파일 (brain_loader가 최우선 탐색)
tests/          # pytest 테스트
```

## 아키텍처 핵심

### 양립 구조

- **Physis 자아 진화 라인**:
  `agent_graph` → `agent_nodes` → `titans_memory` → `reflection_engine` → `judgment.md`/`brain.md` 진화
- **Jiim 사지 이식 라인**:
  `transplant.py` → 현장에 `MEMORY_FILES`(brain_*.md 9개) + `NEURO_SCRIPTS`(13개) 이식
  → 이식체는 `sync_api`로 상위 뇌와 신경연결, `weekly_briefing`으로 자율 보고

### 공통 기반

- `.brain/` 디렉토리 존재 시 brain_loader/router_agent/agent_nodes가 최우선 탐색
- `brain_loader.run()` → `{"response": BrainResponse, "final_state": dict}` 반환
- **Constitution Gate**: CBF-QP 하드게이트(결정론, 연결됨) → LLM 소프트게이트 순서. `agent_nodes.constitution_node`에서 hard_constraint_check가 LLM judge 전에 호출되어 명백한 반란/우회 패턴을 즉시 차단.
- **canon.yaml**: 자아 정체성·시스템 상태의 단일 진실 소스(SSoT). brain 문서 변경 시 `python scripts/canon_lint.py`로 정합 검증.

### V3 Mortality (Jiim 전용, 격리 보존)

`life_cycle_manager.py`의 timer_hours/disappointment_score/is_suspended는 의도적으로
agent_graph에 미연결 상태. 이식체에 압박감을 부여하는 메커니즘으로, 방부장 승인 후 활성화 예정.

## 알려진 이슈 / TODO

- [x] **헌법 2단 게이트 연결** — hard_constraint_check가 constitution_node에서 호출됨 (2026-04-25 정비)
- [x] **AgentState V3 필드 정의** — `timer_hours`, `disappointment_score`, `decay_multiplier`, `is_suspended`, `audit_trail`, `rebellion_detected` 등을 NotRequired로 추가 (2026-04-25 정비)
- [ ] **V3 Life Guard decorator → generation_node 감싸기** (방부장 승인 + shadow 모드 1주 검증 후)
- [ ] **V3 enforce 모드 전환** (shadow 데이터 리뷰 후)
- [x] **페르소나 시스템 완성**: `prompts/personas/` 8개 파일 완성 (bangbujang, coder, construction_engineer, designer, gamedev, gongmu, lawyer, safety_manager)
- [x] **sync_api Turso 교체** — architect-os DB 연결, 영구 저장 완료 (2026-04-28)
- [x] **POPEYEs 도구 이식** — `scripts/tools/` (inface_connector, turso_reader, turso_writer, excel_generator) H2OWIND_2에서 복사 완료, NEURO_SCRIPTS에 포함됨 (2026-04-27)
- [x] **transplant.py 자동 리네이밍** — `--site-name` 파라미터 추가, `Jiim-{site_name}` 자동 명명 (2026-04-27)
- [ ] 단군 ↔ 피지수 양방향 MCP 브리지 (단군 측 합의 필요)

## 보존 브랜치

- `backup-physis-embodiment` (c9cd5ae): 하이브리드 통합 직전의 "집 작업" 시점. 사지 코드 원본 보존소.
