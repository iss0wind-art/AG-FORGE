"""
주간 전략 브리핑 생성기 — weekly_briefing.py
매주 월요일 07:00 방부장님 전용 자동 보고서.
"""
from __future__ import annotations

from scripts.alert_node import detect_alerts


def generate_briefing(weekly_data: list[dict]) -> str:
    if not weekly_data:
        return "이번 주 데이터가 없습니다."

    total_workers_sum = sum(d["summary"]["total_workers"] for d in weekly_data)
    total_공수_sum = sum(d["summary"]["total_공수"] for d in weekly_data)
    days = len(weekly_data)
    avg_workers = total_workers_sum / days
    avg_공수 = total_공수_sum / days

    all_alerts = []
    for d in weekly_data:
        for a in detect_alerts(d):
            all_alerts.append(f"  - [{d['date']}] {a['message']}")

    # 생산성 추세
    first_prod = weekly_data[0]["productivity"]["avg_공수_per_worker"]
    last_prod = weekly_data[-1]["productivity"]["avg_공수_per_worker"]
    trend = last_prod - first_prod
    trend_str = f"+{trend:.3f}" if trend >= 0 else f"{trend:.3f}"
    trend_label = "상승" if trend > 0 else ("하락" if trend < 0 else "보합")

    # 권고사항
    recommendations = []
    if trend < -0.02:
        recommendations.append("생산성 하락 추세 — 팀별 현장 점검 권고")
    if any(len(d["summary"].get("teams_missing", [])) > 0 for d in weekly_data):
        recommendations.append("미보고 팀 발생 이력 있음 — 보고 체계 점검 필요")
    if not recommendations:
        recommendations.append("정상 운영 중. 현상 유지.")

    dates = f"{weekly_data[0]['date']} ~ {weekly_data[-1]['date']}"

    lines = [
        f"# 주간 브리핑 ({dates})",
        "",
        "## 주간 요약",
        f"- 총 투입 공수: {total_공수_sum:.1f}",
        f"- 일 평균 인원: {avg_workers:.0f}명",
        f"- 일 평균 공수: {avg_공수:.1f}",
        f"- 생산성 추세: {trend_str} ({trend_label})",
        "",
        "## 리스크 & 경보",
        *(["\n".join(all_alerts)] if all_alerts else ["  - 이상 없음"]),
        "",
        "## 권고사항",
        *[f"  - {r}" for r in recommendations],
    ]

    return "\n".join(lines)
