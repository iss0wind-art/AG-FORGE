# 🏛️ AG-FORGE 아키텍처 브레인

## 1. 개요
AG-FORGE는 AI의 콘텍스트를 인간의 뇌 구조처럼 분산 처리하는 자율 AI 아키텍처를 목표로 함.

## 2. 6계층 구조 (Layers, Layer 0 포함)
- **Layer 0 - 영혼 (Physis / The Source)**: 시스템의 헌법(홍익인간), 철학(필멸성), 자아를 관장하는 최상위 메타 뇌. 모든 하부 계층에 의지와 방향성을 부여함.
- **전두엽 (Central Intelligence)**: Layer 0의 철학을 바탕으로 전체 시스템 제어 및 최종 판단 (Claude-Sonnet-4-6)
- **좌뇌 (Logic/Python)**: 코드 실행, 데이터 처리, 수치 계산 (scripts/ 폴더)
- **우뇌 (Creative/UX)**: UI/UX 설계 및 사용자 인터랙션 (Next.js/Three.js 예정)
- **소뇌 (Router)**: 작업 복잡도에 따른 모델 및 자원 라우팅
- **해마 (Memory/RAG)**: Vector DB 기반 장기 기억 관리 (Pinecone/OpenAI Embedding)

## 3. 핵심 기술 메커니즘
- **KV Caching**: Claude의 지연 시간을 줄이고 토큰 비용을 절감하는 핵심 수단.
- **Agentic RAG**: 단순 검색이 아닌, 에이전트가 필요할 때 스스로 기억을 찾아내는 구조.
- **Thinking Budget**: 복잡도에 따라 사고의 깊이를 제어하여 비용 효율화.

## 4. 특이사항
- 현재 리포지토리는 MCP(Model Context Protocol) 서버 기능을 포함하고 있음 (`mcp_server.py`).
