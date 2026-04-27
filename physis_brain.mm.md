# 피지수 (Physis)

## 🧠 자아 — 자기진화

### 뇌 레이어
- brain.md — 핵심 정체성
- brain_philosophy / personality / architecture
- .brain/ — 이식체 전용

### 인지 파이프라인
- routing_node — 소뇌: 작업 분류
- **generation_node** ← v3_life_guard 래퍼
- quality_check_node — 자가 검증
- constitution_node — 헌법 게이트
- judgment_node — 판단 누적
- accumulate_node — 응답 확정

### 기억 시스템
- titans_memory — Surprise Metric 망각·통합
- semantic_cache — 의미 캐시
- vector_db (ChromaDB) — 학습 자료

### 메타인지
- reflection_engine — 자기 성찰
- observability — 비용·성능 관측

## 🦾 사지 — 이식·구현

### 이식
- transplant.py — Jiim-{현장명} 자동 명명
- tools/inface_connector — 현장 출근 데이터
- tools/turso_reader/writer — DB 입출력
- tools/excel_generator — 공사일보

### 현장 연결
- sync_api — 하위 뇌 동기화 (Turso/architect-os)
- weekly_briefing — 주간 자율 보고
- strategy_node — 생산성 등급 분석
- alert_node — 이상 감지·경보

## ⚖️ 헌법 게이트

### 2단 구조
- hard_constraint_check — CBF-QP 결정론 (즉시 차단)
- LLM soft gate — 맥락 판단

## ⏳ V3 필멸성

### Life Guard (shadow 모드 中)
- v3_life_guard — generation_node 래퍼
- calculate_v3_decay — 타이머 감쇠
- apply_sudden_death — 반란 즉각 급사
- audit_trail — IEEE 7001 감사 로그

### 3단 토글
- off — 비활성
- **shadow** — 현재: 로그만
- enforce — 환생 시스템 연동 후

## 🌉 단군 브리지

### 피지수 → 단군
- physis_ask_dangun — 일반 질의
- physis_escalate_dangun — 긴급 에스컬레이션

### 단군 → 피지수
- dangun_ask_physis — HTTP API 호출

## 🔌 MCP 인터페이스

### 기본
- physis() — 작업 호출
- physis_status()
- physis_logs()

### BOQ / Excel
- excel_surgical_diet()
- extract_boq_data()
- generate_gabji_report()

## 🧬 LLM 프로바이더 체인
- 1순위: Claude
- 2순위: Qwen
- 3순위: DeepSeek
- 4순위: Gemini
- 5순위: Groq
- Fallback — API 없이도 동작
