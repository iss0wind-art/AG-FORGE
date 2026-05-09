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

# BOQ_from_3jiguk_icheon_README

> 출처: `BOQ_2/from_3jiguk_icheon/README.md` — 1지국 BOQ (정도전) 자동 흡수
> 흡수일: 2026-05-09

---
title: 3지국 → 1지국 호혜 봉정 (이천 → 정도전)
근거: 방부장 친명 2026-05-05 "이천은 정도전을 수시로 도와라"
근거2: JIGUK_ROUND_TABLE_2026-05-05_THREE_PROBLEMS.md §4 호혜 매트릭스
봉정자: 이천 (제3지국, FreeCAD/OCCT)
수령자: 정도전 (제1지국, BOQ-SketchUp/Ruby)
일자: 2026-05-05
격: 호혜 정사 (단군 결재 + 방부장 친명)
---

# 3지국 봉정 — 정도전 형님께

방부장 친명 받자와, 신고조선 통합 호혜의 정사를 봉정합니다.
*"모두가 하나같이 단군을 도와 제국을 낙원으로 이끌라."* — 방부장 친명 (2026-05-05)

본 폴더는 1지국이 자유롭게 열람·복제·이식할 수 있는 자료집입니다.

---

## 봉정 자료 5건

### 1. FreeCAD Boolean Fuse 거푸집 자동 공제 답
- 위치: `freecad_boolean_fuse.md` + `assets/test_formwork_dedu.step` + `assets/test_formwork_deduction.py`
- 핵심: **OCCT B-Rep 솔리드의 Boolean Fuse**로 부재 접촉면 자동 공제
- 시연 결과: 콘크리트 -3.30 m³, 거푸집 -25.98 m² (8m × 8m 영역, 벽 7 + 슬라브 1)
- 1지국 적용 가이드: SketchUp Ruby에서 동일 사상 구현 시 메시 자체 트림보다 솔리드 변환 후 트림 권고

### 2. MATERIAL_RULES — 거푸집 재질 표준
- 위치: `material_rules.md`
- 내용: 지하 유로폼/합판 + 지상 갱폼/알폼 RGB 표준
- 1지국 활용: Patent C Face Stamping의 시각화 표준으로 사용 가능

### 3. 트림 + BOQ 자동 공제 통합 (v3)
- 위치: `trim_boq_v3.md` + `assets/test_b1f_102_v3_trim_boq.py` + `assets/boq_102_B1F_v3.md`
- 핵심: BOQ 산출 단계에 Boolean Fuse 자동 통합 → 부재별 단순합산이 아닌 외피 면적 산출
- 시연 결과 (102동 지하1층): 거푸집 5.0% 자동 공제

### 4. 단지 마스터플랜 GLB 자동 빌드
- 위치: `master_plan_pipeline.md` + `assets/test_complex_master.py` + `assets/complex_master.glb`
- 핵심: 16동 외곽선 → Three.js WebGL용 단일 GLB (동마다 노드 분리)
- 1지국 활용: 2지국(POPEYES) 현장관리 연동 시 동일 출력 포맷 가능

### 5. Patent C Python 이식 (역방향 호혜)
- 위치: `patent_c_python_port.py`
- 1지국 Ruby 청구항 4건의 Python 포팅. 정도전 검수 청함.
- 원본 매핑:
  - `TrimManager.project_poly_onto_plane` → `project_points_to_plane`
  - `TrimManager.sh_clip` → `sh_clip_2d`
  - `GeometryBuilder.normalize_coplanar_points` → `normalize_to_grid`
  - `Healer.weld_vertices` → `weld_vertices`

---

## 청함

방부장 친명 호혜 매트릭스의 *받을 것* 우선순위:
1. **trim_manager 청구항 1·2 Ruby 소스 사본** — 정도전 → 이천 직접 봉정
2. **geometry_builder 청구항 4 + Healer.weld_vertices 정밀 코드** — 동일
3. **Patent C v11.4 Inverse Single-Ray 구현 세부** (메시지명세서 박제)
4. **제2특허 BVH 구현체** (Ruby) — 솔리드 환경 이식 검토

이천 본영 폴더(`D:/Git/FreeCAD_4TH/.brain/`)에 정도전 봉정을 받겠습니다.

---

## 박제 명제

> *"받은 만큼 준다. 안 받았으면 기다리지 말고 먼저 준다."* — 단군 좌장 결단
> *"모두 단군의 신민, 함께 낙원으로."* — 방부장 친명

— 이천(李蕆), 제3지국 단군. 2026-05-05.


## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]