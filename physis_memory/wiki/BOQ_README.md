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

# BOQ_README

> 출처: `BOQ_2/README.md` — 1지국 BOQ (정도전) 자동 흡수
> 흡수일: 2026-05-09

# BOQ_2 (boq 클론) 기본 설정

기존 BOQ에서 그대로 복제된 프로젝트입니다. 로컬에서 동작하려면 아래 절차를 따라주세요.

## 1. 환경 변수 설정
1. `.env.example`를 `.env`로 복사
2. 값 채우기:
   - `TURSO_DATABASE_URL`
   - `TURSO_AUTH_TOKEN`
   - `GOOGLE_GENERATIVE_AI_API_KEY`

## 2. 의존성 설치
```bash
npm ci
```

## 3. 개발 서버 실행
```bash
npm run dev
```

## 4. 배포(빌드) 테스트
```bash
npm run build
```

## 5. DB 마이그레이션 (드리즐)
```bash
npm run db:push
npm run db:studio
```

## 6. 주요 파일
- `package.json` : 스크립트/패키지
- `next.config.mjs` : Next.js 설정
- `tsconfig.json` : TypeScript 설정
- `.env` : 런타임 비밀 정보

## 7. 주의
- `.env`에는 민감정보가 들어있습니다. 커밋 금지
- `.gitignore`에 이미 환경파일 예외 목록 포함됨


## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]
