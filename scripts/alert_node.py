"""
상위 뇌 이상 감지 노드 — alert_node.py
하위 뇌 보고에서 경보 조건을 탐지한다.
"""
from __future__ import annotations

_PRODUCTIVITY_DROP_WARNING = -0.10
_PRODUCTIVITY_DROP_CRITICAL = -0.20
_MISSING_TEAMS_WARNING = 2


def detect_alerts(report: dict) -> list[dict]:
    """보고 데이터에서 이상 징후를 탐지하고 경보 목록을 반환한다."""
    alerts = []
    prod = report["productivity"]
    summary = report["summary"]
    vs_last = prod["vs_last_week"]
    missing = summary.get("teams_missing", [])

    # 생산성 하락 감지
    if vs_last <= _PRODUCTIVITY_DROP_CRITICAL:
        alerts.append({
            "level": "critical",
            "code": "PRODUCTIVITY_CRITICAL_DROP",
            "message": f"생산성 급락 {vs_last:.1%} (기준 -20%) — 즉각 현장 점검 필요",
        })
    elif vs_last <= _PRODUCTIVITY_DROP_WARNING:
        alerts.append({
            "level": "warning",
            "code": "PRODUCTIVITY_WARNING_DROP",
            "message": f"생산성 하락 {vs_last:.1%} (기준 -10%) — 해당 팀 확인 요망",
        })

    # 미보고 팀 감지
    if len(missing) >= _MISSING_TEAMS_WARNING:
        alerts.append({
            "level": "warning",
            "code": "TEAMS_MISSING",
            "message": f"미보고 팀 {len(missing)}개: {', '.join(missing)}",
        })

    return alerts
