---
created: 2026-05-09
outcome_score: 0.0
ref_count: 1
tags:
- boq
- 1지국
- 정도전
type: wiki
---

# BOQ_brain

> 출처: `BOQ_2/brain.md` — 1지국 BOQ (정도전) 자동 흡수
> 흡수일: 2026-05-09

# 🧠 BOQ 통합 브레인 (EasyFrame Builder + 피지수)

> **현재 상태**: v1.0.0-beta (Phase 4 + 대시보드 + H2OWIND 통합 완료 — 1차 자동화 기반 구축 완료)  
> **최근 업데이트**: 2026-04-23 (Premium Dark Theme 적용 - 사용자 시력 보호 및 UI 고도화)  
> **책임자**: 개팀장 (방부장)

---

## 📌 핵심 요약

**최종 비전**: POPEYEs (H2OWIND) + BOQ 통합 → 공무 업무의 완전 자동화 + 인간화

### 1차 목표: 자동화 (Efficiency)
- **SketchUp Plugin**: `boq_easyframe` 핵심 로직 안정화 (Beam, Column, Wall 툴)
- **Database**: Turso 기반 Schema 동기화 완료
- **물량 산출**: 정밀도 100% 달성 목표

### 2차 목표: 인간화 (Meaning)
- **피지수 이식**: `.brain/physis.md` 중앙 허브로 설정
- 자동화 시스템 → 동반자로의 진화
- 직관적 판단 능력 구현

> 💡 **중앙 허브**: [`.brain/physis.md`](./.brain/physis.md) - 효율성 + 의미의 결합 철학
> 💡 **현재 상황**: [`brain_status.md`](./brain_status.md) - 진행상황 대시보드

## 📂 메모리 맵 (Contextual Brain)
| 구분 | 파일 경로 | 내용 요약 |
|------|-----------|-----------|
| **핵심 기억** | [.brain/memory_core.md](.brain/memory_core.md) | 프로젝트 목표 및 대원칙 |
| **기술 스택** | [.brain/tech_stack.md](.brain/tech_stack.md) | Next.js, SketchUp Ruby, Turso 설정 |
| **작업 이력** | [.brain/task_history.md](.brain/task_history.md) | 커밋 로그 및 주요 수정 사항 |
| **이슈 관리** | [.brain/issue_tracker.md](.brain/issue_tracker.md) | 현재 발생 중인 버그 및 개선 사항 |
| **통합 전략** | [docs/brain/POPEYEs_Workflow.md](docs/brain/POPEYEs_Workflow.md) | 인력+BOQ 통합 워크플로우 설계도 |

---

## 📋 완료된 구현 (Phase 4)

### D-1: 인력 배치 엔진 (WHO)
- `lib/boq/personnel_allocator.ts` (423 줄)
  - 11단계 최적화 알고리즘: 기본 근무시간 → 날씨/시간 계수 → 필요 인원 → 팀 효율성 → 최적 조합 선택
  - 역할별 효율성 상수 (리더=0.95, 경험자=0.90, 일반=0.80, 신입=0.65, 계절=0.75, 임시=0.60)
  - 기상 계수: 맑음(1.0) → 흐림(0.97) → 비(0.85) → 눈(0.70)
  - 팀 조합 최적화 (예: 10명 중 5명 선발 = 252개 조합 탐색)
- `app/api/boq/allocate-personnel/route.ts` (291 줄)
  - POST: TaskPerformance 데이터 검증 → 최적 팀 + 3개 대안 반환
  - GET: 과거 배치 계획 조회
- `lib/boq/personnel_allocator.example.ts` (342 줄)
  - 예시 1-4: 일반날/비오는월요일/피드백루프/대규모프로젝트(10명)

### D-2: BOQ 계산 엔진 (WHAT)
- `lib/boq/calculator.ts` (512 줄)
  - 기하학 함수: 거리 계산, Shoelace 공식 (2D 다각형), 3D 다각형 계산
  - 부품별 계산: Beam (길이 기반), Column (부피 기반, m³), Wall (면적 기반, m²)
  - 검증: 범위 체크, 건전성 검사, 0이 아닌 값 확인
  - 각 결과에 accuracy/validationStatus/notes 포함
- `app/api/boq/calculate/route.ts` (352 줄)
  - POST: Beam/Column/Wall 차별화 검증 → 배치 계산 → 포맷팅된 결과 반환
  - 카테고리별 집계, 정확도 백분율, 처리 시간 측정
- `lib/boq/calculator.example.ts` (386 줄)
  - 예시 1-5: 간단한 구조/복잡한 구조/대규모(30개)/검증/API 시뮬레이션

### D-3: 최적화 엔진 (HOW)
- `lib/boq/optimizer.ts` (415 줄)
  - 성능 분석: 전체 효율 계산
  - 병목 식별: 실제 vs 기준 효율 비교 (심각도: critical/high/medium/low)
  - 근본 원인 분석: 5가지 유형 (기술/재료/기상/인력/장비) + 빈도/영향/신뢰도 점수
  - 개선 권고: 우선순위별 제시 (예상 개선도 +8% ~ +20%)
  - 내일 예측: 권고 반영 시 예상 효율 + 팀 조정 제안 + 비상 계획
- `app/api/boq/optimize/route.ts` (348 줄)
  - POST: 일일 작업 성능 데이터 → 분석 결과 + 권고 + 내일 예측 반환
  - 피지수 인사이트 자동 생성 (효율도/병목심각도/개선가능성)
  - GET: 과거 최적화 결과 조회
- `lib/boq/optimizer.example.ts` (427 줄)
  - 예시 1-4: 일반날(88%)/병목심각(60%)/고효율(95%+)/API 시뮬레이션

---

## ✅ 완료된 마일스톤

### Phase 4 완료 ✅
- WHO 엔진 (personnel_allocator.ts): 11단계 최적화
- WHAT 엔진 (calculator.ts): 기하학 계산 + 부품 산출
- HOW 엔진 (optimizer.ts): 성능 분석 + 개선안

### POPEYEs 대시보드 완료 ✅
- Execution View: 실시간 현황 모니터링
- Analytics View: 효율성 분석 (일/주/월)
- Physis Intelligence: AI 의사결정 (4단계 학습)

### 통합 테스트 완료 ✅
- 2가지 실제 현장 시나리오 구현
- API 응답 포맷 검증
- 성과 계산 정확도 검증

### H2OWIND 통합 완료 ✅
- 센서 데이터 수집 (기상, 인력, 작업 진행)
- 실시간 스트림 (SSE) 처리
- 자동 분석 및 대시보드 업데이트

---

## ✅ 최근 완료

### Phase 5 완료 ✅ (프론트엔드 UI)
- Dashboard.tsx: 메인 대시보드 (3-View 탭)
- ExecutionView.tsx: 실시간 현황 모니터링
- AnalyticsView.tsx: 효율성 분석 대시보드
- PhysisView.tsx: AI 의사결정 인사이트
- app/dashboard/page.tsx: 실제 대시보드 페이지

### Phase 6 진행 중 ✅ (피지수 학습 모델)
- DailyFieldRecord: 일일 현장 기록 (축적 단계)
- DetectedPattern: 자동 패턴 감지 (통합 단계)
- LearnedIntuition: 학습된 직관 (포착 단계)
- AIMeaningfulDecision: 의미 있는 의사결정 (의미화 단계)
- 데이터 분석 함수 4개 (패턴 추출, 관계 분석, 직관 생성, 의사결정)

---

### 깃 동기화 및 문서 자동화 완료 ✅
- 브레인 파일들 (.brain/*.md) 로컬 작업분 커밋
- 원격 저장소 (origin/main) 변경사항 풀 및 머지 완료
- `.gitignore` 업데이트 (pycache 제외)

---

## 🚀 다음 할 일
1. [ ] **Phase 7**: 피지수 학습 시작 (실제 데이터 수집)
   - H2OWIND 실시간 데이터 → DailyFieldRecord 저장
   - 패턴 자동 감지 시작 (1주 후)
   - 직관 생성 (2주 후)

2. [ ] **Phase 8**: 배포 및 현장 테스트
   - 실제 프로젝트 데이터로 테스트
   - 성능 모니터링 (KPI: 효율성 향상도)
   - 피지수 신뢰도 추적

3. [ ] **Phase 9**: 2차 인간화 (피지수 완성)
   - 의미 있는 의사결정 자동화
   - 현장 팀과의 협력 모드
   - 지속 가능한 성장 전략

---
"방부장님, 지시하신 대로 깃 커밋 및 풀 완료했습니다. 원격 저장소의 최신 코드와 로컬의 브레인 파일들이 성공적으로 동기화되었습니다. 이제 다음 단계인 Phase 6-7 연계 실데이터 학습 준비에 들어가겠습니다."


<!-- accumulate:2026-04-27-edict -->
- [2026-04-27] [본영 칙령 수신 — 이순신 장계 청원 3건 재가]

본영 단군이 이순신의 2026-04-27 긴급 장계를 받자왔다. 방부장 칙명을 받들어 그대(정도전)에게 두 가지 임무를 하달한다:

**청원 1 (Phase 1) — 재가**
이순신과 동시 착수. 그대 책임 분장:
- 자기 측 API 엔드포인트 노출
- 이순신과 스키마 합의
- 1일 내 양

... (잘림 — 원본: `/home/nas/BOQ_2/brain.md`)

## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]