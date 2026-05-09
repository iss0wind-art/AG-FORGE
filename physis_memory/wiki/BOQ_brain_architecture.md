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

# BOQ_brain_architecture

> 출처: `BOQ_2/brain_architecture.md` — 1지국 BOQ (정도전) 자동 흡수
> 흡수일: 2026-05-09

# 🧠 브레인: 시스템 아키텍처 및 코어 엔진 (Architecture & Core Engine)

## 🏢 계층 및 WBS 구조 (Hierarchy & WBS) [v5.0]

모든 부재는 아웃라이너 내에서 엄격한 계층 구조를 가집니다.

### 1. 폴더 명명 규칙
- **정규 부재**: `[동_층_부재]` (예: `[101D_1F_Wall]`)
- **미분류 부재**: `[UN_UN_TY]` (Unknown_Unknown_Type)
- **목적**: 
  - 물량 산출 시 공간(WBS) 필터링 속도 향상.
  - 아웃라이너 가독성 극대화 및 수동 정리 부담 제거.

### 2. 정규화 엔진 (Normalize All)
- **작동 원리**: 모든 객체의 월드 좌표(`Transformation`)를 보존하면서 부모 폴더를 강제 재배치합니다.
- **좌표 보존**: `target_inv_tr * world_tr` 행렬 연산을 통해 위치 이동 없이 정렬만 수행합니다.

## ✂️ 절단 및 재구성 엔진 (Trim & Reconstruction)

### 1. Slab Method (Sutherland-Hodgman)
- **개념**: `intersect_with`의 불확실성을 제거하기 위해 수학적인 평면 분할 알고리즘을 사용합니다.
- **과정**: 모든 기하학을 볼륨(Volume)이 아닌 면(Face) 덩어리로 인식하고, 커터의 면들을 따라 순차적으로 깎아냅니다.

### 2. EntitiesBuilder 엔진
- **특징**: 스케치업의 자동 병합(Auto-Merge) 문제를 피하기 위해, 연산 중에는 가상 빌더 내에서 기하학을 완성한 후 일괄 생성합니다.
- **성능**: 대규모 부재 생성 시 `disable_ui`와 결합하여 BugSplat을 100% 방어합니다.

## 🛡️ 가드 로직 (Guard Logic)
- **Tolerance Snapping**: `0.001"` 허용 오차를 넘는 미세 오차를 `snap_to_su_tolerance` 함수로 강제 보정합니다.
- **Non-Standard Detection**: 규격에 맞지 않는 부재(예: 면이 뒤집히거나 구멍 난 면)는 산출 대상에서 제외하여 데이터 오염을 방지합니다.


## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]