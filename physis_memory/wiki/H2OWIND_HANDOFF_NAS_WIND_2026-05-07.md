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

# H2OWIND_HANDOFF_NAS_WIND_2026-05-07

> 출처: `H2OWIND_2/HANDOFF_NAS_WIND_2026-05-07.md` — 2지국 H2OWIND (이순신) 자동 흡수
> 흡수일: 2026-05-09

# 나스 배포 핸드오프 — 풍속 자동저장 적용

> 작성: 이순신 | 2026-05-07

## 목적

시간별 풍속 데이터 Turso 자동저장 기능을 나스(리눅스 민트)에 적용하고, crontab 자동 수집을 등록한다.

---

## Step 1 — 코드 pull & 빌드

```bash
cd ~/h2owind   # 또는 프로젝트 경로
git pull
npm run build
```

---

## Step 2 — 서버 재시작 (구동 방식 확인 후 선택)

### PM2를 쓰는 경우
```bash
pm2 list              # 앱 이름 확인
pm2 restart h2owind   # 앱 이름에 맞게 변경
```

### systemd를 쓰는 경우
```bash
sudo systemctl restart h2owind
```

### 직접 실행 중인 경우
```bash
# 기존 프로세스 확인
ps aux | grep node

# 포트 3000 점유 프로세스 종료
kill $(lsof -t -i:3000)

# 재시작
npm run start &   # 또는 npm run dev &
```

### 구동 방식 모르는 경우 — 아래 명령으로 확인
```bash
pm2 list 2>/dev/null && echo "PM2 사용 중"
systemctl list-units --type=service | grep -i node
ps aux | grep node
```

---

## Step 3 — DB 테이블 확인 (이미 생성됨, 건너뛰어도 됨)

Turso는 클라우드 DB라서 테이블은 이미 존재한다. 확인만 하려면:

```bash
node -e "
const { createClient } = require('@libsql/client');
require('dotenv').config({ path: '.env.local' });
const c = createClient({ url: process.env.TURSO_DATABASE_URL, authToken: process.env.TURSO_AUTH_TOKEN });
c.execute('SELECT COUNT(*) as cnt FROM HourlyWind').then(r => console.log('HourlyWind 레코드 수:', r.rows[0].cnt));
"
```

> 5256 이상이면 정상 (2025-10-01~2026-05-07 기적재)

---

## Step 4 — crontab 등록 (핵심)

매일 18:30에 당일 풍속 데이터를 서버가 자동 수집한다.

```bash
crontab -e
```

아래 줄 추가:

```cron
30 18 * * * curl -s http://localhost:3000/api/wind/collect >> /var/log/h2owind-wind.log 2>&1
```

저장 후 확인:
```bash
crontab -l | grep wind
```

---

## 수동 테스트

서버가 뜬 후 아래로 즉시 수집 테스트:

```bash
curl http://localhost:3000/api/wind/collect
# 응답 예: {"date":"2026-05-07","saved":24}
```

특정 날짜 저장 데이터 조회:
```bash
curl "http://localhost:3000/api/wind/collect?date=2026-05-07"
```

---

## 완료 체크리스트

- [ ] git pull 완료
- [ ] npm run build 완료
- [ ] 서버 재시작 완료
- [ ] curl 테스트 응답 확인
- [ ] crontab 등록 완료


## 연결
- [[홍익인간]]
- [[신고조선_제국_전체_구조]]
- [[3지국장_정체성]]


## 연결

- [[홍익인간]]
