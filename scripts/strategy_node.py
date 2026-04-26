"""
상위 뇌 전략 분석 노드 — strategy_node.py
하위 뇌 보고를 받아 생산성 등급·권고사항을 산출한다.
"""
from __future__ import annotations


_GRADE_THRESHOLDS = [
    (0.95, "A"),
    (0.85, "B"),
    (0.75, "C"),
    (0.60, "D"),
]


def _grade(avg_공수: float) -> str:
    for threshold, grade in _GRADE_THRESHOLDS:
        if avg_공수 >= threshold:
            return grade
    return "F"


def _recommend(report: dict) -> str:
    prod = report["productivity"]
    summary = report["summary"]
    vs_last = prod["vs_last_week"]
    missing = summary.get("teams_missing", [])

    parts = []
    if vs_last <= -0.20:
        parts.append("생산성 급락 원인 분석 및 현장 점검 필요")
    elif vs_last <= -0.05:
        parts.append("생산성 소폭 하락 — 해당 팀 작업 현황 확인 권고")

    if len(missing) >= 3:
        parts.append(f"미보고 팀 {len(missing)}개 — 즉시 확인 요청")
    elif missing:
        parts.append(f"미보고 팀: {', '.join(missing)}")

    if not parts:
        parts.append("정상 운영 중. 현상 유지.")

    return " / ".join(parts)


def analyze_report(report: dict) -> dict:
    """하위 뇌 보고를 분석하여 등급과 권고사항을 반환한다."""
    avg_공수 = report["productivity"]["avg_공수_per_worker"]
    grade = _grade(avg_공수)
    recommendation = _recommend(report)

    return {
        "productivity_grade": grade,
        "avg_공수": avg_공수,
        "recommendation": recommendation,
        "total_workers": report["summary"]["total_workers"],
        "teams_missing_count": len(report["summary"].get("teams_missing", [])),
    }
