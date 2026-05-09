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

# H2OWIND_docs_SECURITY_INCIDENTS

> 출처: `H2OWIND_2/docs/SECURITY_INCIDENTS.md` — 2지국 H2OWIND (이순신) 자동 흡수
> 흡수일: 2026-05-09

﻿# 🛡️ POPEYES 보안 사건 기록

> 공개된 위협이 아니라 **향후 의사결정을 위한 기록**이다. Private 레포라도 히스토리와 협업자/연동 경로로 누출 가능성이 있으므로 기록해둔다.

---

## 사건 #001 — `auth_key.json` (Google Service Account 개인키) git 커밋

| 항목 | 내용 |
|------|------|
| 최초 커밋 | `ddfd21c` — 2026-03-17 00:03 KST |
| 커밋 메시지 | [방부장] 2단계 팝아이즈 스마트 관제 및 자재관리 구축 완료 |
| 작성자 | iss0wind-art (프로젝트 오너) |
| 원격 저장소 | github.com/iss0wind-art/h2owind (**PRIVATE**) |
| 푸시 여부 | origin/main 에 존재 |
| 파일 내용 | Google Service Account JSON (project_id: `h2owind-popeyes`, private_key 포함) |
| 발견 시점 | 2026-04-22 POPEYES 전수조사 (Phase 1, Sonnet-C) |

### 조치 현황
- 2026-04-22: `.gitignore`에 `auth_key.json`, `*_service_account.json` 추가
- 2026-04-22: `git rm --cached auth_key.json` 실행 — 로컬 파일 보존, 인덱스에서만 제거 (스테이징 상태, 아직 커밋되지 않음)
- **보류** (사용자 결정): Google Cloud Console 키 폐기·재발급, git history 정리(BFG / git-filter-repo), force-push

### 리스크 재평가 메모
- **외부 공개 유출 아님** — 레포가 PRIVATE이므로 인터넷 일반 검색/클론 불가
- **잠재 위협 경로**:
  - 레포 협업자 권한을 가진 GitHub 계정이 있다면 그들은 이력 전체 열람 가능
  - Claude Code GitHub App, Vercel, CI/CD 등 레포에 연결된 외부 서비스의 토큰이 탈취되면 이력 접근 가능
  - 향후 실수 또는 정책 변경으로 Public 전환 시 즉시 외부 노출
- **Google Cloud 측 관찰**: 해당 키는 유효한 상태. Console > IAM > 서비스 계정 키에서 `client_email = popeyes@h2owind-popeyes.iam.gserviceaccount.com` 권한 범위 확인 필요
- **히스토리 잔존 기간**: 2026-03-17 ~ 현재 (약 5주)

### 유사 키의 `.env.local` 위치
`GOOGLE_PRIVATE_KEY`, `GOOGLE_SERVICE_ACCOUNT_EMAIL`이 `.env.local`에도 존재함. 즉 Next.js 앱은 `.env.local`을, scripts/ 일회성 스크립트들은 `auth_key.json`을 참조하는 이중 경로가 설계되어 있었음. 재발급 시 두 곳 모두 교체 필요.

### 재발 방지
- `.gitignore`에 `auth_key.json`, `*_service_account.json`, `**/*_key.json`, `**/credentials.json` 추가 완료
- 신규 민감 파일 추가 시 `.gitignore` 사전 등록 체크리스트 권고

---

## 사건 #002 — `NEXT_PUBLIC_H2O_API_KEY` 클라이언트 번들 노출

| 항목 | 내용 |
|------|------|
| 발견 시점 | 2026-04-22 Phase 2 실행 중 (.env.local 확인 과정) |
| 파일 | `.env.local` (27행) |
| 값 | `NEXT_PUBLIC_H2O_API_KEY=h2o-wind-site-manager-2026` (H2O_API_KEY와 동일) |

### 성격
- Next.js의 `NEXT_PUBLIC_` 프리픽스는 빌드 시점에 **브라우저 번들에 인라인된다**.
- zrok 공개 터널로 노출된 사이트이므로, 누구든 접속 후 DevTools > Network/Sources 탭에서 이 키를 **평문으로 열람 가능**.
- 결과적으로 이 키는 "공개 상수"이며, `X-H2O-API-KEY` 헤더 검증을 무력화한다.

### 사용처
- `app/components/hooks/useConcretePour.ts` — /api/dashboard/store 호출 시 헤더
- `app/components/ConcretePouringStatus.tsx`
- `app/components/MonthlyGanttChart.tsx`

### 조치 현황
- 2026-04-22: H2O_API_KEY와 NEXT_PUBLIC_H2O_API_KEY를 새로운 랜덤 값으로 **로테이션**. 다만 `NEXT_PUBLIC_` 프리픽스 자체가 유지되므로 이는 **기존 키의 기밀성 회복용**이 아니라 **"첫 번째 값을 알던 사람만 통과"** 문제를 제거한 정도의 조치.
- `lib/apiAuth.ts`는 이 키 하나로 GET 외 요청을 인증하는 구조 유지.

### 보류 (사용자 결정 필요, 아키텍처 재설계 수준)
클라이언트에서 API 인증이 필요한 호출의 근본 해결 방향 3가지:
1. **세션 기반 인증 도입** — 로그인 → 쿠키 → 서버 검증 (별도 로그인 UI 필요)
2. **서버 액션/라우트로 경유** — 클라이언트 직접 fetch → server action 호출로 바꿔 키를 서버에서만 붙임 (파일 수정 범위 큼)
3. **해당 엔드포인트를 정말 공개** — `/api/dashboard/store` 등이 zrok 외부에서 자유 접근되어도 괜찮다면 `PUBLIC_GET_PATHS`에 추가하고 NEXT_PUBLIC_ 키 제거 (단, POST/PUT은 여전히 문제)

→ Phase 3 아키텍처 과제로 분리.

---

## 사건 #003 — `lib/apiAuth.ts` 하드코딩 폴백 키

| 항목 | 내용 |
|------|------|
| 발견 시점 | 2026-04-22 Phase 1 (Sonnet-A, Sonnet-C 이중 확인) |
| 파일 | `lib/apiAuth.ts:14` |
| 폴백 값 | `'h2o-wind-site-manager-2026'` |

### 조치
- 2026-04-22 Phase 2: 하드코딩 폴백 제거, `H2O_API_KEY` env 미설정 시 즉시 throw.
- GET 무조건 허용 정책 → `PUBLIC_GET_PATHS` allow-list 방식으로 전환 (단, 현재 allow-list는 기존 GET 경로 전부 포함하는 임시값).

### 후속 과제 (Phase 3)
`PUBLIC_GET_PATHS`를 실제로 공개해도 안전한 경로만 남기고 축소 심사.

---

## 운영 체크리스트 (매 배포 전)

- [ ] `.env.local`, `.env`에 비밀값이 실제로 로드되는지 — `H2O_API_KEY`, `ADMIN_SECRET`, `INFACE_ID`, `INFACE_PW`
- [ ] `auth_key.json`이 `.gitignore`에 등록된 상태 유지
- [ ] `NEXT_PUBLIC_` 프리픽스 env에 비밀값이 들어가지 않았는지 (프리픽스는 공개 상수용)
- [ ] `git log --all --full-history -- <민감파일명>` 으로 추가 유출 없는지 점검


## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]