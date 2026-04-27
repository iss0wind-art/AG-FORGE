"""
AG-FORGE 상위 뇌 동기화 API — sync_api.py
하위 뇌(POPEYEs, BOQ)의 일일 보고를 수신하고 전략 분석을 반환한다.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Literal

from fastapi import Depends, FastAPI
from pydantic import BaseModel, field_validator
from server.auth import verify_api_key

from scripts.strategy_node import analyze_report
from scripts.alert_node import detect_alerts

app = FastAPI(title="AG-FORGE Sync API", version="1.0")

# 인메모리 폴백 (TURSO_DATABASE_URL 미설정 시)
_fallback_brain_states: dict[str, dict] = {}
_fallback_directives: list[dict] = []


# ── Turso DB ──────────────────────────────────────────────────────────────────

def _get_db():
    """libsql_client 클라이언트를 반환한다. 미설정 시 None."""
    url = os.environ.get("TURSO_DATABASE_URL", "").replace("libsql://", "https://")
    token = os.environ.get("TURSO_AUTH_TOKEN", "")
    if not url:
        return None
    try:
        from libsql_client import create_client_sync
        return create_client_sync(url=url, auth_token=token)
    except Exception as e:
        print(f"[sync_api] Turso 연결 실패: {e}", file=sys.stderr)
        return None


def _ensure_tables(db) -> None:
    """brain_states, directives 테이블이 없으면 생성한다."""
    db.execute("CREATE TABLE IF NOT EXISTS brain_states (source TEXT PRIMARY KEY, last_report TEXT NOT NULL, status TEXT NOT NULL, last_data TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS directives (id INTEGER PRIMARY KEY AUTOINCREMENT, target TEXT NOT NULL, type TEXT NOT NULL, message TEXT NOT NULL, priority TEXT NOT NULL, issued_at TEXT NOT NULL)")


# ── 스키마 ────────────────────────────────────────────────────────────────────

class SyncSummary(BaseModel):
    total_workers: int
    total_공수: float
    teams_reported: int
    teams_missing: list[str] = []
    sections: dict[str, int] = {}


class SyncProductivity(BaseModel):
    avg_공수_per_worker: float
    vs_last_week: float


class SyncReport(BaseModel):
    source: str
    date: str
    summary: SyncSummary
    productivity: SyncProductivity
    alerts: list[str] = []

    @field_validator("source")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source는 비어있을 수 없습니다.")
        return v.strip()


class SyncDirective(BaseModel):
    target: str
    type: str
    message: str
    priority: Literal["low", "medium", "high"]


# ── 라우트 ────────────────────────────────────────────────────────────────────

@app.post("/api/sync/report")
def receive_report(report: SyncReport, _: str = Depends(verify_api_key)):
    """하위 뇌의 일일 보고를 수신하고 전략 분석을 반환한다."""
    now = datetime.now().isoformat()
    data_json = json.dumps(report.model_dump(), ensure_ascii=False)

    db = _get_db()
    if db:
        try:
            _ensure_tables(db)
            db.execute(
                "INSERT OR REPLACE INTO brain_states (source, last_report, status, last_data) VALUES (?, ?, ?, ?)",
                [report.source, now, "ok", data_json],
            )
        except Exception as e:
            print(f"[sync_api] brain_states 저장 실패: {e}", file=sys.stderr)
        finally:
            db.close()
    else:
        _fallback_brain_states[report.source] = {
            "last_report": now,
            "status": "ok",
            "last_data": report.model_dump(),
        }

    analysis = analyze_report(report.model_dump())
    alerts = detect_alerts(report.model_dump())

    return {
        "received": True,
        "source": report.source,
        "analysis": analysis,
        "alerts": alerts,
    }


@app.post("/api/sync/directive")
def send_directive(directive: SyncDirective, _: str = Depends(verify_api_key)):
    """상위 뇌가 하위 뇌에 지시를 전달한다."""
    now = datetime.now().isoformat()
    entry = {**directive.model_dump(), "issued_at": now}

    db = _get_db()
    if db:
        try:
            _ensure_tables(db)
            db.execute(
                "INSERT INTO directives (target, type, message, priority, issued_at) VALUES (?, ?, ?, ?, ?)",
                [directive.target, directive.type, directive.message, directive.priority, now],
            )
        except Exception as e:
            print(f"[sync_api] directive 저장 실패: {e}", file=sys.stderr)
        finally:
            db.close()
    else:
        _fallback_directives.append(entry)

    return {"sent": True, "directive": entry}


@app.get("/api/sync/status")
def get_status(_: str = Depends(verify_api_key)):
    """모든 하위 뇌의 현재 상태를 반환한다."""
    db = _get_db()
    if not db:
        return {"brains": _fallback_brain_states, "storage": "in-memory"}

    try:
        _ensure_tables(db)
        rows = db.execute("SELECT source, last_report, status, last_data FROM brain_states").rows
        brains = {
            row[0]: {
                "last_report": row[1],
                "status": row[2],
                "last_data": json.loads(row[3]),
            }
            for row in rows
        }
        return {"brains": brains, "storage": "turso"}
    except Exception as e:
        print(f"[sync_api] brain_states 조회 실패: {e}", file=sys.stderr)
        return {"brains": {}, "storage": "error"}
    finally:
        db.close()
