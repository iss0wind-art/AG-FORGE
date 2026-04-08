# AG-Forge: Multi-Layer Brain Architecture

**Version**: 1.0 (_기획팀 & 리팀장 전달용_)  
**Date**: 2026년 4월 8일  
**Status**: 🔴 리팀장 결재 대기

---

## 📌 프로젝트 개요

**AG-Forge**는 Claude AI의 콘텍스트를 인간의 뇌 구조(좌뇌/우뇌/전두엽/소뇌/해마)처럼 분산 처리하는 **자율 AI 아키텍처**입니다.

### 핵심 목표
- 🧠 정보 과부하 방지 & 최적의 판단력 유지
- ⚡ 토큰 비용 90% 절감 (KV 캐싱 + Vector RAG)
- 🔄 Level 3 자율성: 스스로 판단 → 기억 검색 → 비용 최적화
- 📊 실시간 모니터링으로 할루시네이션 차단

---

## 📂 문서 구조

| 파일 | 목적 |
|------|------|
| **CONSTITUTION.md** | **[기반] 홍익인간 0원칙 — 모든 시스템의 뿌리. 방부장만 개정 가능** |
| **architecture-overview.md** | 5계층 뇌 아키텍처 + 데이터 흐름도 |
| **technical-guidelines.md** | 4가지 기술적 통제 장치 상세 설명 |
| **implementation-roadmap.md** | 리팀장 주도의 단계별 구현 계획 |
| **brain-layer-reference.md** | 각 계층(brain/logic/emotion/judgment/library)의 역할 상세 |
| **cost-optimization-guide.md** | 토큰 비용 계산 & 최적화 검사표 |

---

## 🎯 리팀장(최태산)을 위한 Quick Start

### 1단계: 구조 이해 (30분)
```bash
Read: architecture-overview.md
      ↓
Understand: 5 brain layers + 4 technical mechanisms
```

### 2단계: 기술 설계 (1시간)
```bash
Read: technical-guidelines.md
      ↓
Design: Vector DB schema + Cache strategy + Router rules
```

### 3단계: 구현 계획 (2시간)
```bash
Read: implementation-roadmap.md
      ↓
Create: Sprint tasks + dependency graph + resource allocation
```

---

## ⚠️ 방부장 체크사항 (최종 결재 전)

- [ ] Vector DB (Redis/Pinecone) 비용 견적 확인
- [ ] KV 캐싱 API 문서 검토 (Claude API 최신 버전)
- [ ] Router 에이전트 토큰 오버헤드 계산
- [ ] LangSmith/OpenTelemetry 라이센스 확인
- [ ] 초기 파일럿 (1주) 커스트 추정

---

## 📞 담당자

| 역할 | 담당자 | 연락처 |
|------|---------|--------|
| 기획 총괄 | 기획팀 | (기획팀) |
| 기술 구현 | 리팀장(최태산) | **(이 문서 수령 후 액션 개시)** |
| 최종 결재 | 방부장 | **(기술 설계 완료 후 결재)** |

---

## 🚀 다음 액션 (리팀장)

1. ✅ 이 README와 architecture-overview.md 읽기
2. ✅ technical-guidelines.md의 4가지 메커니즘 기술 검토
3. ✅ implementation-roadmap.md 기반 프로젝트 계획 수립
4. ✅ 초기 프로토타입 (Vector RAG 1주)으로 타당성 검증
5. ✅ 방부장 최종 결재 신청

---

**"단순 코딩이 아니라, 뇌를 설계한다는 기분으로 작업하라"**
