---
type: wiki
created: 2026-05-09
tags: [boq, 실패, 폐기, 회고, 학습자료]
ref_count: 0
outcome_score: 0.0
---

# FAIL_BOQ_LEGACY_CONTEXT

> 🔴 실패·폐기·롤백 흔적
> BOQ 레거시 컨텍스트
> 출처: `/home/nas/BOQ_2/docs/legacy/LEGACY_CONTEXT.md`

# 📦 과거 유산 맥락 정리 (LEGACY_CONTEXT.md)

> **작성일**: 2026-04-03
> **목적**: 시스템 퍼지(Purge) 대상 파일들의 핵심 맥락 보존 및 폐기 기록

## 📂 폐기된 백업 및 임시 파일 리스트

### 1. `old_page_utf8.tsx` / `src/app/page_backup.tsx`
- **맥락**: 메인 대시보드 리팩토링 과정에서 생성된 구버전 UI 소스.
- **핵심 정보**: 초기 데이터 바인딩 로직 및 MUI(Material UI) 중심의 테이블 구성 방식이 포함되어 있었으나, 현재는 `App Router` 구조의 `page.tsx`로 완전히 대체됨.
- **상태**: 폐기 완료 (2026-04-03)

### 2. `before_revert_backup.rb.txt` / `.tmp_trim_stable.rb`
- **맥락**: Ruby 플러그인의 `trim_manager.rb` 최적화 및 리팩토링 직전의 스냅샷.
- **핵심 정보**: 비파괴 투영 알고리즘의 초기 안정 버전 코드. 현재는 `dist_plugin/` 산하의 최신 버전으로 통합됨.
- **상태**: 폐기 완료 (2026-04-03)

### 3. 기술 검증용 Python 스크립트군 (`check2.py`, `check_coords.py` 등)
- **맥락**: BOQ 데이터 정합성 확인을 위한 케이스별 검증 스크립트.
- **핵심 정보**: 코어 로직은 `check.py`에 통합되었으며, 특정 좌표계 검증 등은 단위 테스트 코드로 승계됨.
- **상태**: 통합 후 폐기 완료 (2026-04-03)

## 💡 개팀장의 판단
과거의 파편화된 백업본은 현재의 '단일 진실 공급원(Single Source of Truth)' 원칙에 위배되므로 맥락만 본 문서에 남기고 물리적 파일은 모두 삭제 처리하였습니다.


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
