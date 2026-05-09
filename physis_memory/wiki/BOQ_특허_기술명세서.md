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

# BOQ_특허_기술명세서

> 출처: `BOQ_2/특허_기술명세서.md` — 1지국 BOQ (정도전) 자동 흡수
> 흡수일: 2026-05-09

# BOQ EasyFrame 특허 기술 명세서
> 추출일: 2026-03-24 | 소스: 코드 내 청구항 코멘트 자동 추출

---

## 발명 개요

**발명 명칭**: 3D BIM 모델 기반 건축 골조 거푸집 물량 자동 산출 시스템
**구현 환경**: SketchUp Ruby API
**핵심 모듈**: `trim_manager.rb`, `geometry_builder.rb`, `boq_generator.rb`, `math_helper.rb`

---

## 트림 엔진 청구항 (trim_manager.rb)

### 청구항 1 — 비파괴 선 투영 (Non-Destructive Line Projection)

> cutter 부재 전체 꼭짓점을 target 면 평면으로 **수직 정사영(Orthogonal Projection)**

**수식**:
```
P' = P - [(P - P0) · n̂] × n̂
```
- `P` : cutter 꼭짓점 (world 좌표)
- `P0` : target 면 위의 임의 점
- `n̂` : target 면의 단위 법선 벡터
- `P'` : 정사영된 점

**의의**: 기존 Boolean Subtraction 방식(파괴적)과 달리, 원본 형상을 훼손하지 않고 접합 경계만 계산. 모델 무결성 유지.

**구현 위치**: `TrimManager.project_poly_onto_plane`

---

### 청구항 2 — Sutherland-Hodgman 다각형 클리핑

> 정사영된 실루엣 ∩ target 면 경계 → **교차 다각형 산출**

**알고리즘**:
```
for each clip_edge (A→B) of target_face:
  edge_norm = face_normal × edge_dir   ← CCW 기준 내측 법선
  판정: (P - A) · edge_norm >= 0 → 내부
  내부↔외부 전환점에서 교점 삽입 (선분-평면 교점)
```

**의의**: 임의 각도 교차, 비직각 접합부에서도 정확한 클리핑 다각형 산출. 복잡 형상(ㄱ자, 十자, 斜交) 대응.

**구현 위치**: `TrimManager.sh_clip`, `TrimManager.seg_plane_intersect`

---

### 청구항 3 — 경계선 삽입 / 면 자동 분할 → Water Stamp 연계

> 클리핑 결과를 target entities에 `add_line` → SketchUp 자동 면 분할
> → Water Stamp가 분할된 면을 **노출면(거푸집)** vs **접합면(공제)**으로 분류

**흐름**:
```
[Trim] SH 클리핑 결과 다각형
  → local 좌표 변환 (target_tr_inv 적용)
  → target_ents.add_line(p1, p2) 반복
  → SketchUp 엔진이 face 위 edge 감지 → 자동 face 분할
  → [Water Stamp] 분할면 법선 방향 raytest → 재질 분배
```

**속성 기록**:
- `BOQ_TRIM/split_lines` : 삽입된 경계선 수
- `BOQ_TRIM/trim_count` : 트림 처리 횟수

**구현 위치**: `TrimManager.perform_actual_trim` (lines_to_add 처리 구간)

---

### 청구항 4 — SH 슬라이스 적분 실측 체적 공제 (BOQ 리포트용)

> AABB 근사를 폐기하고 **SH(Sutherland-Hodgman) Z축 슬라이스 적분**으로 두 부재의 실측 교차 체적을 산출해 `deduction_m3` 속성에 누적
> `nil` 반환 시 AABB 폴백 유지 (비정형 형상 안전망)

**알고리즘 (R-1, MAX_SLICES=20)**:
```
for k in 0..19:
  z_mid = z_lo + (k + 0.5) × dz
  poly_a = slice_box_at_z(cutter.bounds, z_mid)   ← 단면 사각형
  poly_b = slice_box_at_z(target.bounds, z_mid)   ← 단면 사각형
  area += polygon_area_2d(SH_clip(poly_a, poly_b))
volume_in3 = area × dz   ← SketchUp 내부 단위(in³)
```

**단위 변환 (SketchUp 내부 단위 → m³)**:
```
overlap_m3 = volume_in3 × (1.inch.to_m)³   ← 0.0254³ ≈ 1.6387e-5
```

**속성 기록**:
- `BOQ_TRIM/deduction_m3` : 누적 공제 체적 (m³)
- `BOQ_TRIM/trim_count` : 누적 트림 횟수

**의의**: 복잡한 형상(사선 부재, 비직교 교차)에서 AABB 대비 정밀도 향상.
         `nil` 반환 시 AABB 폴백으로 안전망 유지.

**구현 위치**: `TrimManager.perform_actual_trim` (R-1 실측 체적 공제 구간)

---

## 거푸집 판정 청구항 (geometry_builder.rb)

### 청구항 1 — OBB Slab 알고리즘 기반 교차 판별

> 분기 없는 OBB(Oriented Bounding Box) Slab 알고리즘 (Tavian Barnes Part 3 최적화)
> 레이-OBB 교차 판별에 적용

**구현 위치**: `GeometryBuilder` (line ~557)

---

### 청구항 2 — 법선 벡터 내적 기반 비-매니폴드 방어 레이캐스팅

> 면의 법선 방향으로 레이를 발사해 인접 부재를 탐지.
> 자기 면(Self-Hit) 및 비-매니폴드 엣지 오탐 방지를 위해 **Adaptive Offset** 적용

**핵심 로직**:
```
adaptive_offset = min(0.1mm, shortest_edge × 0.01)
probe_origin = face_center.offset(face_normal, -adaptive_offset)
max_probe_dist = max(entity.bounds.diagonal, 500mm)
```

**자기 면 필터링**: 3회 반복, `distance < adaptive_offset × 1.5` 이내 히트 무시

**구현 위치**: `GeometryBuilder.detect_dominance`

---

### 청구항 3 — 불연속 UV 좌표 생성

> 거푸집 재질 적용 시 면 단위로 독립적인 UV 매핑 생성
> 연속 면에서 텍스처 왜곡 방지

**구현 위치**: `GeometryBuilder.create_beam_with_builder` (UV mapping 구간)

---

### 청구항 4 — 부동소수점 오차 흡수용 공간 그리드 정규화

> 건축 도면 좌표(mm 단위)에서 발생하는 부동소수점 누적 오차를 **0.001mm 그리드**로 정규화

**수식**:
```
normalized = round(value / tol) × tol    (tol = 0.001mm)
```

**구현 위치**: `GeometryBuilder.normalize_coplanar_points`, `Healer.weld_vertices`

---

## BOQ 산출 청구항 (boq_generator.rb)

### 청구항 1 — 외곽선 데이터 추출 및 분할 경계선(Boundary Edge) 생성

> 부재 그룹에서 노출 외곽 엣지를 추출해 거푸집 영역 경계를 정의

**구현 위치**: `BOQGenerator` (line ~336)

### 청구항 2 — 내적 기반 비-매니폴드 방어 레이캐스팅

> 물질 우선순위(Priority) 검사 시 비-매니폴드 면에서 오탐 방지

**구현 위치**: `BOQGenerator` (line ~433)

### 청구항 3 — 분할된 면의 은폐면(Hidden Face) 식별을 위한 기하학적 검증

> 트림으로 분할된 face 중 다른 부재 내부에 위치한 은폐면을 기하학적으로 판별

**구현 위치**: `BOQGenerator` (line ~337)

---

## 슬랩 알고리즘 청구항 (math_helper.rb)

### 특허 S210~S220 — 슬랩 알고리즘 기반 교차 판별 엔진

> 레이-박스 교차 판별에 특화된 슬랩(Slab) 알고리즘 최적화 구현

**구현 위치**: `MathHelper` (line ~5)

---

## Water Stamp 엔진 (geometry_builder.rb — v2.0)

> **트림과 독립적으로 작동**하는 재질 분배 엔진
> 모든 BOQ 부재의 면에 거푸집 / 콘크리트 속살 재질을 사후 일괄 적용

**판정 로직**:
```
for each face F of member M (priority P_m):
  probe = F.center + F.normal × 5mm        ← 셀프히트 완전 회피
  hit = model.raytest(probe, F.normal)

  if hit && distance < 500mm:
    hit_priority = DOMINANCE_TABLE[hit_member.type]
    if hit_priority > P_m  → :JOINT (콘크리트 

... (잘림 — 원본: `/home/nas/BOQ_2/특허_기술명세서.md`)

## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]