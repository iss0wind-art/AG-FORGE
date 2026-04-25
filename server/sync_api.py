"""
AG-FORGE 상위 뇌 동기화 API — sync_api.py
하위 뇌(POPEYEs, BOQ)의 일일 보고를 수신하고 전략 분석을 반환한다.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from scripts.strategy_node import analyze_report
from scripts.alert_node import detect_alerts

app = FastAPI(title="AG-FORGE Sync API", version="1.0")

# 인메모리 상태 저장소 (운영 시 Turso로 교체)
_brain_states: dict[str, dict] = {}
_directives: list[dict] = []


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
def receive_report(report: SyncReport):
    """하위 뇌의 일일 보고를 수신하고 전략 분석을 반환한다."""
    _brain_states[report.source] = {
        "last_report": datetime.now().isoformat(),
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
def send_directive(directive: SyncDirective):
    """상위 뇌가 하위 뇌에 지시를 전달한다."""
    entry = {
        **directive.model_dump(),
        "issued_at": datetime.now().isoformat(),
    }
    _directives.append(entry)
    return {"sent": True, "directive": entry}


@app.get("/api/sync/status")
def get_status():
    """모든 하위 뇌의 현재 상태를 반환한다."""
    return {"brains": _brain_states}
