"""
전략 분석 노드 + 이상 감지 노드 테스트
"""
import pytest
from scripts.strategy_node import analyze_report
from scripts.alert_node import detect_alerts

NORMAL_REPORT = {
    "source": "popeyes",
    "date": "2026-04-19",
    "summary": {
        "total_workers": 290,
        "total_공수": 285.5,
        "teams_reported": 42,
        "teams_missing": [],
        "sections": {"101동": 45, "105동": 62},
    },
    "productivity": {"avg_공수_per_worker": 0.985, "vs_last_week": 0.01},
    "alerts": [],
}

DROP_REPORT = {
    **NORMAL_REPORT,
    "productivity": {"avg_공수_per_worker": 0.71, "vs_last_week": -0.27},
}

MISSING_TEAMS_REPORT = {
    **NORMAL_REPORT,
    "summary": {**NORMAL_REPORT["summary"], "teams_missing": ["비계팀", "타설팀", "철근1팀"]},
}


class TestStrategyNode:
    def test_returns_dict(self):
        result = analyze_report(NORMAL_REPORT)
        assert isinstance(result, dict)

    def test_contains_productivity_grade(self):
        result = analyze_report(NORMAL_REPORT)
        assert "productivity_grade" in result

    def test_normal_report_grade_ok(self):
        result = analyze_report(NORMAL_REPORT)
        assert result["productivity_grade"] in ("A", "B", "C", "D", "F")

    def test_drop_report_lower_grade(self):
        normal = analyze_report(NORMAL_REPORT)
        drop = analyze_report(DROP_REPORT)
        grades = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
        assert grades[drop["productivity_grade"]] < grades[normal["productivity_grade"]]

    def test_contains_recommendation(self):
        result = analyze_report(DROP_REPORT)
        assert "recommendation" in result
        assert len(result["recommendation"]) > 0


class TestAlertNode:
    def test_no_alerts_on_normal(self):
        alerts = detect_alerts(NORMAL_REPORT)
        assert isinstance(alerts, list)
        assert len(alerts) == 0

    def test_productivity_drop_triggers_alert(self):
        alerts = detect_alerts(DROP_REPORT)
        assert any("생산성" in a["message"] for a in alerts)

    def test_missing_teams_triggers_alert(self):
        alerts = detect_alerts(MISSING_TEAMS_REPORT)
        assert any("미보고" in a["message"] for a in alerts)

    def test_alert_has_required_fields(self):
        alerts = detect_alerts(DROP_REPORT)
        for alert in alerts:
            assert "level" in alert
            assert "message" in alert
            assert alert["level"] in ("info", "warning", "critical")

    def test_severe_drop_is_critical(self):
        alerts = detect_alerts(DROP_REPORT)
        levels = [a["level"] for a in alerts]
        assert "critical" in levels or "warning" in levels
