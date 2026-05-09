---
created: 2026-05-09
outcome_score: 0.0
ref_count: 1
tags:
- h2owind
- 2지국
- 이순신
type: wiki
---

# H2OWIND_DATA_FLOW

> 출처: `H2OWIND_2/DATA_FLOW.md` — 2지국 H2OWIND (이순신) 자동 흡수
> 흡수일: 2026-05-09

# H2OWIND 데이터 흐름 맵
> 2026-04-30 기준 · 이순신(H2OWIND 지국) 작성
> 🟢 정상 · 🟡 주의 · 🔴 단절/심각 · ⬛ 사실상 미사용

---

## 전체 흐름 개요

```mermaid
flowchart TD
    classDef ok       fill:#1a472a,stroke:#4ade80,color:#fff
    classDef warn     fill:#713f12,stroke:#facc15,color:#fff
    classDef dead     fill:#450a0a,stroke:#f87171,color:#fff,stroke-dasharray:6 2
    classDef local    fill:#1e3a5f,stroke:#60a5fa,color:#fff
    classDef external fill:#312e81,stroke:#a78bfa,color:#fff
    classDef display  fill:#1e1b4b,stroke:#818cf8,color:#fff

    %% ══════════════════════════════════
    %% 1. 데이터 입력원
    %% ══════════════════════════════════
    INFACE([🏭 인페이스\n외부 출역 시스템]):::external
    TEAMLEADER([👷 팀장\n/team/input]):::external
    ADMIN([🖥️ 관리자\n메인 대시보드]):::external

    %% ══════════════════════════════════
    %% 2. DB 테이블
    %% ══════════════════════════════════
    subgraph DB["🗄️ Turso DB"]
        INFACE_RAW[(InfaceRawData\n처리된 명단 JSON)]:::ok
        WORKER[(Worker\n근로자 마스터)]:::ok
        DAILY_WORKER[(DailyWorker\n일일 출역)]:::warn
        TEAM_REPORT[(TeamReport\n팀 일보)]:::ok
        WORK_LOG[(DailyWorkLog\n작업 내용)]:::ok
        DAILY_OUTPUT[(DailyOutput\n공종별 집계)]:::warn
        MASTER_REPORT[(MasterReport\n공사일보 취합)]:::dead
        ZONE[(ZonePrediction\nAI 구간예측)]:::ok
        NOTICE[(Notice\n공지사항)]:::ok
        SAFETY[(DailyInspection\n안전점검)]:::ok
    end

    %% ══════════════════════════════════
    %% 3. 브라우저 localStorage
    %% ══════════════════════════════════
    subgraph LOCAL["💾 localStorage (브라우저)"]
        L_ITEMS[daily-output-data-DATE\n인페이스 명단]:::local
        L_REPORTS[smart-job-reports\n🔴 유령 170건 잔존]:::dead
    end

    %% ══════════════════════════════════
    %% 4. 화면 표시
    %% ══════════════════════════════════
    subgraph VIEW["📺 화면"]
        DASHBOARD[출력명단\n팀별현황]:::display
        VIEWER[소장님 뷰어\n/viewer]:::display
        ARCHIVE[일출 기록 보관함\n/reports]:::display
        TEAM_VIEW[팀 대시보드\n공지·현황·공정]:::display
        ZONE_UI[구간예측 UI]:::display
    end

    %% ══════════════════════════════════
    %% 인페이스 흐름
    %% ══════════════════════════════════
    INFACE -->|"① 인양 버튼 클릭"| PROC
    PROC["⚙️ processRawData\n명단 변환·필터"]:::ok
    PROC -->|"처리된 items 저장\n(2026-04-30 fix)"| INFACE_RAW
    PROC -->|"sync-inface upsert"| WORKER
    PROC -->|"일일 출역 기록"| DAILY_WORKER
    PROC -->|"이름 있는 데이터만\n(2026-04-30 fix)"| L_ITEMS

    %% 명단 복구 경로 (우선순위 순)
    L_ITEMS -->|"① 최우선 복구"| DASHBOARD
    INFACE_RAW -->|"② localStorage 없을 때"| DASHBOARD
    DAILY_OUTPUT -->|"③ 최후 폴백\n🟡 이름 없음"| DASHBOARD
    DASHBOARD --> VIEWER

    %% ══════════════════════════════════
    %% 팀 보고 흐름
    %% ══════════════════════════════════
    TEAMLEADER -->|"보고서 제출\nPOST /api/reports"| TEAM_REPORT
    TEAM_REPORT -->|"content 자동 UPSERT"| WORK_LOG
    TEAM_REPORT -->|"승인 시 표시"| TEAM_VIEW
    WORK_LOG -->|"구간예측 AI 학습"| ZONE
    ZONE --> ZONE_UI

    %% ══════════════════════════════════
    %% 관리자 흐름
    %% ══════════════════════════════════
    ADMIN -->|"저장 버튼"| DAILY_OUTPUT
    ADMIN -->|"연동 버튼\nGET /api/reports"| MASTER_REPORT
    MASTER_REPORT -->|"🔴 빈 레코드 주입\n유령 170건 원인"| L_REPORTS
    L_REPORTS -->|"localStorage 직독"| ARCHIVE

    %% ══════════════════════════════════
    %% 기타 흐름
    %% ══════════════════════════════════
    ADMIN -->|"공지 등록"| NOTICE
    NOTICE -->|"팀별 필터링"| TEAM_VIEW
    ADMIN -->|"안전 점검"| SAFETY
    WORKER -->|"/api/site/workers"| VIEWER
```

---

## 흐름별 상세 진단

### 🏭 인페이스 → 출력명단

```mermaid
flowchart LR
    classDef ok   fill:#1a472a,stroke:#4ade80,color:#fff
    classDef warn fill:#713f12,stroke:#facc15,color:#fff
    classDef dead fill:#450a0a,stroke:#f87171,color:#fff,stroke-dasharray:5 3
    classDef fix  fill:#0c4a6e,stroke:#38bdf8,color:#fff

    A([인페이스]):::ok
    B[인양 버튼]:::ok
    C[processRawData]:::ok
    D[(InfaceRawData DB\n처리된 items)]:::fix
    E[localStorage\ndaily-output-data-DATE]:::ok
    F[Worker DB]:::ok
    G[출력명단 화면]:::ok

    A --> B --> C
    C -->|"✅ fix: raw→processed 저장"| D
    C -->|"이름 있는 데이터만\n✅ fix: 집계 차단"| E
    C --> F
    E -->|"① 최우선"| G
    D -->|"② localStorage 없을 때"| G

    H[DailyOutput\n공종별 집계만]:::warn
    H -->|"③ 폴백 — 이름 없음\n→ 23명 표시 버그 ✅수정됨"| G

    I[SSE report_updated]:::warn
    I -->|"🔴 이전: forceDb=true\n→ localStorage 무시 → 명단 날아감\n✅ fix: forceDb 제거"| G
```

**과거 문제**: 팀장이 보고서 제출 → SSE 이벤트 → forceDb=true → localStorage 무시 → DB fallback → 이름 없는 집계 데이터 → 명단 휘발
**현재 상태**: 3중 fix 완료. 인양 1회 후 영구 유지.

---

### 👷 팀장 보고 → 대시보드

```mermaid
flowchart LR
    classDef ok   fill:#1a472a,stroke:#4

... (잘림 — 원본: `/home/nas/H2OWIND_2/DATA_FLOW.md`)

## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]
