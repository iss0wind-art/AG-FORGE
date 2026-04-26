# 상위↔하위 뇌 동기화 프로토콜

---

## 하위 뇌 → 상위 뇌 (일일 보고)

**엔드포인트**: `POST /api/sync/report`  
**시점**: 매일 08:00 (공사일보 생성 완료 후)

```json
{
  "source": "popeyes",
  "date": "2026-04-19",
  "summary": {
    "total_workers": 290,
    "total_공수": 285.5,
    "teams_reported": 38,
    "teams_missing": ["비계보양팀", "그라우팅팀"],
    "sections": {
      "101동": 45,
      "102동": 38,
      "105동": 62
    }
  },
  "productivity": {
    "avg_공수_per_worker": 0.985,
    "vs_last_week": -0.032
  },
  "alerts": []
}
```

---

## 상위 뇌 → 하위 뇌 (지시)

**엔드포인트**: `POST /api/sync/directive`

```json
{
  "target": "popeyes",
  "type": "alert",
  "message": "형틀3팀 생산성 3주 연속 하락. 원인 분석 요청.",
  "priority": "high"
}
```

---

## 상태 조회

**엔드포인트**: `GET /api/sync/status`

```json
{
  "brains": {
    "popeyes": { "last_report": "2026-04-19T08:00:00", "status": "ok" },
    "boq":     { "last_report": "2026-04-19T08:05:00", "status": "ok" }
  }
}
```
