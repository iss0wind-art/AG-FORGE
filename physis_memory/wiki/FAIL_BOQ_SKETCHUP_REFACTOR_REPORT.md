---
created: 2026-05-09
outcome_score: 0.0
ref_count: 1
tags:
- boq
- 실패
- 폐기
- 회고
- 학습자료
type: wiki
---

# FAIL_BOQ_SKETCHUP_REFACTOR_REPORT

> 🔴 실패·폐기·롤백 흔적
> SketchUp 리팩토링 보고서 — 무엇이 실패했나
> 출처: `/home/nas/BOQ_2/SKETCHUP_REFACTOR_REPORT.md`

# SKETCHUP_REFACTOR_REPORT

> **BOQ EasyFrame SketchUp 플러그인 Phase 4 리팩토링 분해 계획서**
> 작성일: 2026-04-23
> 작성 체계: Claude Opus 4.7 (지휘) + Claude Sonnet 4.6 병렬 4 에이전트 (조사) + 피지수 Gemini (자문) + 방부장 (결재)
> 상태: **방부장 결재 대기**

---

## ⚠️ HARD-GATE 선언 (최상위)

> **이 리포트 자체에서 Ruby 코드를 단 한 줄도 수정하지 않는다.**
>
> Phase 4는 설계 산출물 단계다. 리포트에 대한 방부장 결재 수령 후, 아래 4개 분해 작업은 **각각 별도 세션, 별도 결재**로 진행한다. 절대 금지:
> - 결재 없이 다음 순위 자동 착수
> - 한 세션에서 2순위 이상 연속 진행
> - Ralph Loop / 일괄 루프 처리
> - 특허 영역(비파괴 트림 / Water Stamp / BIM 최적화) 코드 이동 시 특허 담당자 이중 결재 생략
>
> 근거: CLAUDE.md 절대 규칙 #1 "방부장 결재 없이 독단 실행 금지", #5 "특허 보호", `golden-principles.md` #9 HARD-GATE, #12 Surgical Changes.

---

## 📑 목차

1. [요약 (Executive Summary)](#1-요약-executive-summary)
2. [현재 구조 실측](#2-현재-구조-실측)
3. [의존성 그래프](#3-의존성-그래프)
4. [특허 청구항 매핑](#4-특허-청구항-매핑)
5. [분해 시뮬레이션](#5-분해-시뮬레이션)
6. [공통 리스크](#6-공통-리스크)
7. [이슈 목록](#7-이슈-목록)
8. [통합 테스트 전략 (스모크 10건)](#8-통합-테스트-전략-스모크-10건)
9. [분해 순서 권고](#9-분해-순서-권고)
10. [역할 분담 매트릭스](#10-역할-분담-매트릭스)
11. [방부장 결재 요청 항목](#11-방부장-결재-요청-항목)

---

## 1. 요약 (Executive Summary)

BOQ EasyFrame SketchUp 플러그인의 `sketchup_plugins/boq_easyframe/src/boq_easyframe/core/` 영역에 있는 800줄 초과 대형 파일 4개(총 **7,185줄**)를 분해하기 위한 설계 문서다.

**분해 대상 파일**

| 파일 | 실측 줄수 | 특허 포함 | 분해 후 예상 파일수 |
|---|---|---|---|
| `geometry_builder.rb` | 3,428 | Water Stamp + BIM 최적화 | 6 (5 + 인터페이스 레이어) |
| `boq_generator.rb` | 1,512 | (위임 래퍼만 포함) | 3 |
| `temporary_works_manager.rb` | 1,317 | (인접 영역) | 2~3 |
| `opening_tools.rb` | 928 | (비파괴 트림 알고리즘 공유) | 3 |

**핵심 발견**

- **Water Stamp 특허 본체는 `geometry_builder.rb`에 있음** (L89–226, L1244–1300). `temporary_works_manager.rb`에는 Water Stamp 코드가 없음 — V2 계획서(`archive/prompt_plan_phase0-3.md`) "temp_works/water_stamp.rb" 분리안은 **실제 코드 위치 기준으로 재설계 필요**.
- **`TexturePainterTool` 중복 정의** (L1894, L2985). Ruby 특성상 뒤쪽이 덮어써서 앞쪽 54줄은 **실행된 적 없는 죽은 코드**. `activate`의 inputbox 재질 선택 기능이 사용자에게 도달하지 못함.
- **순환 의존**: `geometry_builder ↔ boq_generator` 양방향 호출. 현재 `defined?` 가드로 로드 타임만 회피, 런타임 순환 경로 존재.
- **`DOMINANCE_TABLE` 공유 상수**가 `geometry_builder.rb` 최상단에 선언되어 `trim_manager.rb`, `boq_generator.rb` 양쪽에서 참조. 단일 진원지 이동 필수.

**권고 분해 순서** (리스크 오름차순)
1. `opening_tools.rb` (파일럿, 리스크 하)
2. `boq_generator.rb` (리스크 중)
3. `geometry_builder.rb` (리스크 상, Water Stamp + BIM 최적화 특허 격리 포함)
4. `temporary_works_manager.rb` (리스크 상, 특허 인접)

---

## 2. 현재 구조 실측

### 2-1. 파일 크기 Top 10

| 순위 | 파일 | 줄수 |
|---|---|---|
| 1 | `core/geometry_builder.rb` | 3,428 |
| 2 | `core/boq_generator.rb` | 1,512 |
| 3 | `core/temporary_works_manager.rb` | 1,317 |
| 4 | `core/opening_tools.rb` | 928 |
| 5 | `core/cleaner.rb` | 606 |
| 6 | `core/trim_manager.rb` | 596 |
| 7 | `core/math_helper.rb` | 387 |
| 8 | `core/tools/foundation_tool.rb` | 353 |
| 9 | `core/space_manager.rb` | 243 |
| 10 | `core/tools/column_tool.rb` | 227 |

### 2-2. 800줄 max 규칙 초과 현황

- `coding-style.md`, `golden-principles.md` #5 기준 **파일 800줄 max**.
- 초과 파일: 상위 4개 (`geometry_builder`, `boq_generator`, `temp_works_manager`, `opening_tools`). 합계 7,185줄.
- `cleaner.rb` (606), `trim_manager.rb` (596)은 규칙 내이나 리팩토링 여지 있음 (이번 Phase 4 범위 외).

---

## 3. 의존성 그래프

### 3-1. 순방향 의존 (각 파일이 참조하는 내부 모듈)

**`geometry_builder.rb`**
- `Core::SubstanceManager` — `analyze_interface` (L3236)
- `Core::MathHelper` — `split_polygon_by_plane` (L3339)
- `Core::SpaceManager` — `reload_hud_options`, `@@project` (L388, L2597–2622)
- `BOQ::EasyFrame::Core::BOQGenerator` — `apply_smart_texture` (L1924, 2088, 3008, `defined?` 가드)
- `tools/column_tool.rb`, `beam_tool.rb`, `wall_tool.rb`, `slab_tool.rb`, `foundation_tool.rb` — `require_relative` (L1514–1526)

> `opening_tools.rb`는 `require_relative` 없이 `main.rb`가 별도 load하며, 파일 자체가 `module GeometryBuilder` 블록 안에서 reopen되어 GeometryBuilder 네임스페이스에 주입됨.

**`boq_generator.rb`**
- `Core::GeometryBuilder` — `normalize_pt`, `detect_dominance`, `DOMINANCE_TABLE`, `raytest_external_only`, `water_stamp_all`, `get_defn` 등 12건 이상
- `Core::SubstanceManager` — `SUBSTANCES`, `TYPE_TO_SUBSTANCE` 상수 (L426–427)
- 외부 `require` 없음 — `main.rb`의 CORE_LOAD_ORDER에 의존



## 분류
- 지국: boq
- 유형: 실패/폐기/응급복구
- 가치: 미래 해답을 위한 비싼 학습 자료

## 연결
- [[홍익인간]]
- [[3지국장_정체성]]
- [[FAIL_종합_분석]]


## 연결

- [[홍익인간]]
