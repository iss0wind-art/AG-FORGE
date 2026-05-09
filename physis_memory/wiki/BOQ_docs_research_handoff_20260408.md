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

# BOQ_docs_research_handoff_20260408

> 출처: `BOQ_2/docs/research_handoff_20260408.md` — 1지국 BOQ (정도전) 자동 흡수
> 흡수일: 2026-05-09

# 리서치팀 인계 자료 — BOQ EasyFrame (2026-04-08)

> 작성: 개팀장 (방부장 결재 전)  
> 엔진 버전: v11.4 Sniper  
> 목적: 현재 기술 한계 및 연구 과제 공유

---

## 1. 현재 엔진 상태 요약

| 항목 | 상태 |
|------|------|
| 트림 정확도 | **이중 공제 버그 수정 완료** (2026-04-07) |
| 크래시 안정성 | **가드 로직 추가 완료** (법선 계산, valid? 체크) |
| 물량 산출 방식 | **AABB 근사 — 미해결** |
| 트림 성능 | **O(n²) — 미해결** |
| src↔dist 동기화 | 수동 복사 의존 — 자동화 없음 |

---

## 2. 핵심 기술 배경 (v11.4 Sniper)

### Inverse Single-Ray 판정
- 부재 외부 0.1mm 지점에서 중심 방향으로 역방향 레이 1회 발사
- 기존 대비 연산 50% 절감, 조인트 판정 무결점

### Face-Finder 스탬핑
- 레이캐스팅 오차 구간에서 면(Face) 좌표를 직접 추출하여 도장 처리
- 소수점 단위 틈새·겹침도 즉시 공제

### 지배력 서열 (Dominance Hierarchy)
```
Column (100) > Beam (80) > Wall (60) > Slab (40) > Foundation (20)
```
- 교차 지점은 고우선순위 부재가 지배권 획득
- 저우선순위 면 → 속살(JOINT) 재질로 치환 후 물량 제외

---

## 3. 연구 과제 (Research Tasks)

### [R-1] AABB → 실측 볼륨 계산 고도화 ⭐ 최우선

**현재 방식 (문제)**
```
# trim_manager.rb:171 근방
dx = [cb.max.x, tb.max.x].min - [cb.min.x, tb.min.x].max
dy = [cb.max.y, tb.max.y].min - [cb.min.y, tb.min.y].max
dz = [cb.max.z, tb.max.z].min - [cb.min.z, tb.min.z].max
deduct_volume = dx * dy * dz
```

**문제점**  
바운딩박스(AABB) 겹침으로 공제량 근사. 사선 부재, 경사 슬래브에서 실제 교차 체적과 오차 발생.

**연구 방향**  
Sutherland-Hodgman(SH) 클리핑 다각형 기반 실측 교차 체적 계산 알고리즘 도입.  
참고 파일: [trim_manager.rb](../sketchup_plugins/boq_easyframe/src/boq_easyframe/core/trim_manager.rb) — `calc_deduction_volume` 메서드

---

### [R-2] O(n²) → Spatial Grid 최적화 ⭐ 2순위

**현재 병목**
```ruby
# trim_manager.rb:127 — execute_trimming 내 전수 쌍 순회
cutters.each_with_index do |ci_ent, ci|
  targets.each_with_index do |ti_ent, ti|
    # 모든 쌍 검사 → 1,000개 부재 시 1,000,000회 순회
  end
end
```

**목표**  
AABB 기반 Spatial Grid(격자 분할) 도입으로 인접 부재만 검사.  
1,000개+ 부재 대응, 목표 복잡도 O(n log n) 이하.

---

### [R-3] Substance Manager — Raycast 내부 판정

**현재 방식**  
`container.bounds.contains?(point)` — AABB 바운딩박스 판정

**문제점**  
불규칙한 형상의 컨테이너에서 내부/외부 오판정 발생 가능.

**연구 방향**  
Down/Up Raycast 교차 횟수 홀짝 판정(Jordan Curve Theorem) 기반 정밀 내부 판정.  
참고 파일: [substance_manager.rb](../sketchup_plugins/boq_easyframe/src/boq_easyframe/core/substance_manager.rb)

---

## 4. 관련 코어 파일

| 파일 | 역할 |
|------|------|
| `core/trim_manager.rb` | 비파괴 트림 + 물량 공제 엔진 |
| `core/substance_manager.rb` | 지배력 판정 + 재질 분류 |
| `core/geometry_builder.rb` | 기하 생성 + Water Stamp |
| `core/boq_generator.rb` | v11.4 Sniper 메인 오케스트레이터 |

경로 기준: `sketchup_plugins/boq_easyframe/src/boq_easyframe/`

---

## 5. 참고 — 어제 패치 내역 (2026-04-07)

| 수정 내용 | 파일 | 상태 |
|-----------|------|------|
| 동일 타입 이중 공제 방지 (`ci < ti`) | trim_manager.rb | ✅ 완료 |
| 법선 계산 zero-vector 가드 | geometry_builder.rb | ✅ 완료 |
| 무음 rescue → 로그 출력 | trim_manager.rb | ✅ 완료 |
| container.valid? 체크 | substance_manager.rb | ✅ 완료 |
| dist_plugin 누락 파일 12개 동기화 | dist_plugin/ | ✅ 완료 |

---

*문의: 개팀장 / 최종 배포 전 방부장 결재 필요*


## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]