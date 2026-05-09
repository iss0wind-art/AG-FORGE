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

# BOQ_ARCHITECTURE

> 출처: `BOQ_2/ARCHITECTURE.md` — 1지국 BOQ (정도전) 자동 흡수
> 흡수일: 2026-05-09

# 🏛️ 시스템 아키텍처 (ARCHITECTURE.md)

> **프로젝트명**: BOQ 자동화 시스템
> **핵심 원칙**: 타입 안전성, 실시간 3D 렌더링, 대용량 데이터 최적화

## ⚙️ 코어 기술 스택
| 분류 | 기술 | 버전/비고 |
|------|------|-----------|
| **Frontend** | Next.js | 16.1.6 (App Router) |
| **Language** | TypeScript | Strict Mode |
| **Database** | Turso | LibSQL 기반 |
| **ORM** | Drizzle ORM | 타입 안전 쿼리 |
| **3D Engine** | Three.js | React Three Fiber (R3F) |
| **Data I/O** | exceljs | 대용량 Excel 스트림 처리 |

## 🏗️ 주요 아키텍처 규칙
1. **Server/Client Component 분리**: 상주형 관리자 인터렉션과 서버 렌더링 조립
2. **전역 상태**: `zustand` 필수 사용
3. **데이터 정합성**: 소수점 오차 방지를 위해 `DECIMAL(18,6)` 등 수치 계산 규약 준수
4. **이기종 통신**: Node.js ↔ Ruby (SketchUp Plugin) ↔ Python (Verification)

## 📡 외부 연동 (Connectivity)
- **SketchUp Plugin**: Ruby API 기반의 지오메트리 데이터를 WebApp으로 송출
- **Verification Scripts**: Python 기반의 `check.py`, `fix.py`를 통한 모델링 데이터 검증


## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]
