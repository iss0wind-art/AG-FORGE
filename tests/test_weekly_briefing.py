"""주간 브리핑 생성기 테스트"""
import pytest
from scripts.weekly_briefing import generate_briefing

WEEKLY_DATA = [
    {"date": "2026-04-14", "source": "popeyes", "summary": {"total_workers": 285, "total_공수": 280.0, "teams_missing": []}, "productivity": {"avg_공수_per_worker": 0.982, "vs_last_week": 0.01}},
    {"date": "2026-04-15", "source": "popeyes", "summary": {"total_workers": 290, "total_공수": 285.5, "teams_missing": []}, "productivity": {"avg_공수_per_worker": 0.985, "vs_last_week": 0.003}},
    {"date": "2026-04-16", "source": "popeyes", "summary": {"total_workers": 270, "total_공수": 260.0, "teams_missing": ["비계팀"]}, "productivity": {"avg_공수_per_worker": 0.963, "vs_last_week": -0.022}},
    {"date": "2026-04-17", "source": "popeyes", "summary": {"total_workers": 280, "total_공수": 275.0, "teams_missing": []}, "productivity": {"avg_공수_per_worker": 0.982, "vs_last_week": 0.02}},
    {"date": "2026-04-18", "source": "popeyes", "summary": {"total_workers": 288, "total_공수": 284.0, "teams_missing": []}, "productivity": {"avg_공수_per_worker": 0.986, "vs_last_week": 0.004}},
]


class TestWeeklyBriefing:
    def test_returns_string(self):
        result = generate_briefing(WEEKLY_DATA)
        assert isinstance(result, str)

    def test_contains_week_summary(self):
        result = generate_briefing(WEEKLY_DATA)
        assert "주간" in result or "총" in result

    def test_contains_total_공수(self):
        result = generate_briefing(WEEKLY_DATA)
        assert "공수" in result

    def test_contains_risk_section(self):
        result = generate_briefing(WEEKLY_DATA)
        assert "리스크" in result or "주의" in result or "경보" in result

    def test_contains_recommendation(self):
        result = generate_briefing(WEEKLY_DATA)
        assert "권고" in result or "제안" in result

    def test_empty_data_returns_no_data_message(self):
        result = generate_briefing([])
        assert "데이터" in result

    def test_briefing_not_empty(self):
        result = generate_briefing(WEEKLY_DATA)
        assert len(result) > 100
