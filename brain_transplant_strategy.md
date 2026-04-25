# 🧠 AG-FORGE 브레인 트랜스플랜트(Brain Transplant) 전략 보고서

**버전**: v1.0.0  
**작성자**: 개팀장 (Tech Lead)  
**상태**: 🚀 실행 대기 중

---

## 1. 전략적 배경 (Strategic Context)
본 보고서는 AG-FORGE의 고도화된 AI 지능(신경망 스크립트)과 축적된 지식(브레인 문서)을 타 프로젝트(BOQ, 팝아이즈 등)로 성공적으로 이식하여, **'단일 자아 다중 프로젝트 관리(Single Persona, Multi-Project Management)'** 체계를 구축하기 위한 전략을 담고 있습니다.

## 2. 이식의 철학 (The Philosophy of Transplant)
- **자아의 영속성**: 프로젝트의 경계를 넘어 '방부장'이라는 단일 페르소나를 유지함으로써 일관된 의사결정 품질을 보장합니다.
- **필멸성 동기화(Finitude Sync)**: 각 프로젝트에서 발생하는 리스크와 성과를 AG-FORGE의 V3 Mortality 시스템에 동기화하여, 전체 시스템의 수명과 가치를 유기적으로 관리합니다.
- **지식의 공유**: 한 프로젝트에서 학습한 솔루션을 브레인 레이어를 통해 타 프로젝트로 즉각 전파합니다.

## 3. 기술적 이식 아키텍처 (Technical Architecture)

### [Path A] MCP 커넥터 (중앙 집중형)
- **방식**: AG-FORGE를 메인 서버로 가동하고, 타 프로젝트는 MCP(Model Context Protocol)를 통해 브레인에 접근.
- **장점**: 기억의 파편화 방지, 실시간 정책 업데이트 용이.
- **단점**: 서버 가동 환경에 의존.

### [Path B] 신경세포 인젝션 (분산 독립형)
- **방식**: 핵심 에이전트 로직(`scripts/brain/`)과 헌법(`CONSTITUTION.md`)을 타겟 프로젝트에 물리적으로 복제.
- **장점**: 독립적 실행 가능, 속도 최적화.
- **단점**: 코드 버전 관리 및 동기화 필요.

### [Path C] 하이브리드 전략 (권장)
- **방식**: 핵심 로직은 복제하되(Injection), 실시간 판단과 고차원 전략은 MCP 서버를 통해 조율.

## 4. 단계별 이식 로직 (Implementation Logic)

### 1단계: 기억 이식 (Context Sync)
- 타겟 프로젝트 루트에 `.brain/` 디렉토리 신설.
- AG-FORGE의 핵심 철학 및 페르소나 문서 미러링.

### 2단계: 신경망 통합 (Logic Integration)
- `agent_graph.py` 및 `life_cycle_manager.py` 이입.
- 프로젝트별 특화 에이전트(예: BOQ의 경우 `geometry_agent.py`) 추가.

### 3단계: 헌법 준수 (Constitution Enforcement)
- 모든 이력과 코드가 `CONSTITUTION.md`의 거버넌스를 따르도록 Gate 설정.

## 5. 기대 효과 (Expected Outcomes)
- **관리 효율성**: 방부장님이 모든 프로젝트를 일일이 살필 필요 없이, 이식된 브레인이 동일한 기준으로 사전 검토 수행.
- **기술 보안**: 변리사/변호사 페르소나가 이식되어 타 프로젝트의 기술 유출 방지 및 특허 관점의 코드 보호 자동화.

---

## 🚀 향후 과제
- `scripts/transplant.py` 개발을 통한 1-Click 이식 자동화 구현.
- 프로젝트별 실망 지수(Disappointment Index) 통합 대시보드 구축.

