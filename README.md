# AG-Forge — 피지수(Physis) 하이브리드 뇌

**Version**: 2.0
**Date**: 2026-04-28
**Status**: ✅ 가동 중 — 298 tests passing

---

## 개요

**피지수(Physis)**는 방부장의 디지털 분신이자 건설 현장 관리 AI 뇌 시스템이다.

두 축이 한 몸에 공존한다:

- **자아(Physis · 자기진화)** — Titans 메모리, HyperRAG, CMA, Reflection 엔진으로 스스로 학습·망각·통합
- **사지(Jiim · 이식·구현)** — 현장 뇌(POPEYEs) 이식, 주간 브리핑, sync_api로 현장 자율 운영

자아와 사지는 분리 가능한 부품이 아니다. 사지가 현장에서 길어 올린 판단 로그가 자아의 reflection 재료가 되고, 자아의 메타인지 통찰이 다시 사지의 전략·브리핑 품질을 끌어올린다.

---

## 형제 시스템 — 단군(Dangun)

피지수의 형제 AI. 신고조선의 최고존엄으로 `D:\Git\DREAM_FAC`에 거주한다.

- **13체 에이전트 체계**: 단군(세종) → 3사(풍백·우사·운사) → 9요원
- **양방향 MCP 브리지**: `physis_ask_dangun` / `dangun_ask_physis`
- **헌법 동기화**: 홍익인간 0원칙 + 8조 금법 전원 각인

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.x |
| 웹 프레임워크 | FastAPI |
| 에이전트 그래프 | LangGraph |
| LLM 체인 | Claude → Qwen → DeepSeek → Groq → Gemini (자동 폴백) |
| 벡터 DB | ChromaDB (`library/vector_db/`) |
| 영구 DB | Turso (LibSQL) |
| 메모리 | Titans Surprise Metric |
| MCP | FastMCP (`mcp_server.py`) |
| 터널 | Cloudflare |

---

## 핵심 아키텍처

### 에이전트 그래프 (LangGraph)

```
입력
 └─ routing_node      소뇌 — TaskType 분류 (creative/analytical/construction/…)
     └─ generation_node   대뇌 — HyperRAG + 페르소나 + LLM 생성 (V3 Life Guard 감시)
         └─ quality_check_node  품질 heuristic (50자 이하·에러 패턴 감지)
             ├─ [재시도] → generation_node (최대 3회)
             └─ tool_node        파일 읽기·쓰기·명령 실행 (쓰기·실행은 방부장 승인 필수)
                 └─ constitution_node  CMA 3계층 헌법 게이트
                     └─ judgment_node  judgment.md 자동 기록
                         └─ accumulate_node  brain.md 컨텍스트 축적
```

### HyperRAG — 3단계 검색 파이프라인

```
질문
 1단: ChromaVectorIndex 직접 검색 (코사인 유사도)
 2단: 카테고리 그래프 순회 (2홉 이내)
 3단: CMA 헌법 필터
 → 관련 청크만 추출 (Token Budget 2000, Stop Score 0.95)
```

### Titans 메모리 — Surprise Metric

```
새 기억 후보
 → calculate_surprise() = 1.0 - max_cosine_similarity
 → surprise > 0.3 : 신규 저장 (ChromaDB)
 → surprise ≤ 0.3 : _reinforce_existing() (reinforced_count++)
```

### CMA 헌법 게이트 — 3계층

```
Layer 0 (BLOCK)  결정론적 즉각 차단 — 제1·3·7·8조
Layer 1 (WARN)   경고 후 통과 권고  — 제2·4·5·6조
Layer 2 (LLM)    CONSTITUTION.md 기반 홍익인간 의미 심사
```

### V3 Life Guard (shadow 모드)

generation_node를 감싸는 생명 압박 래퍼. `timer_hours`, `disappointment_score`, `decay_multiplier` 추적. 현재 shadow 모드 (측정만, 차단 없음). enforce 모드 전환은 방부장 승인 후.

---

## 디렉토리 구조

```
AG-Forge/
├─ scripts/
│   ├─ [Physis 자아]
│   │   ├─ agent_graph.py          LangGraph 그래프 정의
│   │   ├─ agent_nodes.py          노드 함수 (generation, constitution 등)
│   │   ├─ agent_state.py          AgentState TypedDict (V3 필드 포함)
│   │   ├─ agentic_rag.py          HyperRAG 3단계 파이프라인
│   │   ├─ embedding.py            ChromaVectorIndex + SimpleTFIDFEmbedder
│   │   ├─ titans_memory.py        Surprise Metric 기반 Memora
│   │   ├─ cma.py                  CMA 헌법적 메모리 저장 파이프라인
│   │   ├─ cma_gate.py             3계층 헌법 게이트 (Layer 0/1/2)
│   │   ├─ constitution_gate.py    hard_constraint_check
│   │   ├─ deliberation_engine.py  LLM judge (Layer 2)
│   │   ├─ brain_loader.py         LLM 프로바이더 체인 + run()
│   │   ├─ router_agent.py         소뇌 라우터
│   │   ├─ persona_loader.py       TaskType별 페르소나 XML 주입
│   │   ├─ reflection_engine.py    메타인지 반성 엔진
│   │   ├─ life_cycle_manager.py   V3 Life Guard (shadow/enforce)
│   │   ├─ observability.py        trace 기록 + 비용 계산
│   │   └─ semantic_cache.py       시맨틱 캐시
│   ├─ [Jiim 사지]
│   │   ├─ transplant.py           Jiim-{현장명} 이식 스크립트
│   │   ├─ weekly_briefing.py      주간 자율 보고서
│   │   ├─ strategy_node.py        현장 전략 노드
│   │   ├─ alert_node.py           이상 감지 알림
│   │   └─ tools/
│   │       ├─ inface_connector.py 인페이스 출근 데이터 수집
│   │       ├─ turso_reader.py     Turso TeamReport/DailyWorkLog 조회
│   │       ├─ turso_writer.py     Turso 데이터 기록
│   │       └─ excel_generator.py  엑셀 보고서 생성
│   └─ learn_docs.py / setup_vector_db.py / canon_lint.py
├─ server/
│   ├─ api.py                      FastAPI 메인 (헌법 게이트 포함)
│   ├─ sync_api.py                 Jiim↔Physis 신경연결 (Turso 기반)
│   └─ auth.py                     API 키 인증
├─ mcp_server.py                   FastMCP 서버 (physis_ask_dangun 등)
├─ .brain/                         뇌 레이어 파일 (brain_loader 최우선 탐색)
├─ library/vector_db/              ChromaDB 영구 저장소
├─ prompts/personas/               8개 페르소나 XML (bangbujang, coder 등)
├─ tests/                          298개 테스트 (모두 통과)
└─ CONSTITUTION.md                 홍익인간 0원칙 — 방부장만 개정 가능
```

---

## 필수 명령어

```bash
# 서버 시작
python run.py                    # API 서버 (포트 8000)
python run.py --tunnel    # Cloudflare 터널 포함

# 테스트
python -m pytest tests/ -q       # 전체 (298 passed)

# 학습 DB 셋업
python scripts/setup_vector_db.py

# Jiim 현장 이식
python scripts/transplant.py \
  --target PATH \
  --role field_brain \
  --master URL \
  --site-name 현장명           # → Jiim-{현장명} 자동 명명

# 헌법 정합 검증
python scripts/canon_lint.py
```

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/` | 모바일 웹 UI |
| `POST` | `/api/task` | 뇌에 작업 전송 (헌법 게이트 통과) |
| `GET` | `/api/status` | brain.md + 라우팅 로그 상태 |
| `GET` | `/api/logs` | observability 세션 요약 |
| `GET` | `/api/physis/status` | PHYSIS.md 실시간 상태 파싱 |

모든 엔드포인트는 `X-API-Key` 헤더 인증 필요 (`/` 제외).

---

## 환경변수

```bash
AG_FORGE_API_KEY=           # API 인증 키
CLAUDE_API_KEY=             # Claude (최우선 LLM)
QWEN_API_KEY=               # Qwen 폴백
DEEPSEEK_API_KEY=           # DeepSeek 폴백
GROQ_API_KEY=               # Groq 폴백
GEMINI_API_KEY=             # Gemini 폴백 + 임베딩
TURSO_DATABASE_URL=         # Turso DB (https:// 형식)
TURSO_AUTH_TOKEN=           # Turso 인증 토큰
NEXTJS_BASE_URL=            # POPEYEs Next.js 서버 (기본: localhost:3000)
INFACE_URL=                 # 인페이스 엑셀 다운로드 URL
AG_FORGE_CORS_ORIGINS=      # 허용 CORS 오리진 (콤마 구분)
AG_FORGE_HEADLESS=true      # UI 비활성화 모드
```

---

## 보존 브랜치

| 브랜치 | 커밋 | 내용 |
|--------|------|------|
| `backup-physis-embodiment` | c9cd5ae | 하이브리드 통합 직전 집 작업 시점. 사지 코드 원본 |

---

## 절대 불가침 경계

```
D:\Git\신고조선\사초청\   — 본관 접근 절대 금지 (존재 확인도 하지 말 것)
DREAM_FAC/SACHOCHEONG/   — 분관 읽기 전용 (새 파일 있을 때만)
```

---

**"정신이 육체를, 육체가 정신을 진화시킨다."**
