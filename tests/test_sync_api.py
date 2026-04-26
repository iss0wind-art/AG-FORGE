"""
상위 뇌 동기화 API 테스트
RED → GREEN → REFACTOR
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    from server.sync_api import app
    return TestClient(app)


SAMPLE_REPORT = {
    "source": "popeyes",
    "date": "2026-04-19",
    "summary": {
        "total_workers": 290,
        "total_공수": 285.5,
        "teams_reported": 38,
        "teams_missing": ["비계보양팀"],
        "sections": {"101동": 45, "105동": 62},
    },
    "productivity": {"avg_공수_per_worker": 0.985, "vs_last_week": -0.032},
    "alerts": [],
}


class TestSyncReport:
    def test_report_returns_200(self, client):
        resp = client.post("/api/sync/report", json=SAMPLE_REPORT)
        assert resp.status_code == 200

    def test_report_stored(self, client):
        client.post("/api/sync/report", json=SAMPLE_REPORT)
        resp = client.get("/api/sync/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "popeyes" in data["brains"]

    def test_report_missing_source_rejected(self, client):
        bad = {**SAMPLE_REPORT, "source": ""}
        resp = client.post("/api/sync/report", json=bad)
        assert resp.status_code == 422

    def test_report_triggers_analysis(self, client):
        resp = client.post("/api/sync/report", json=SAMPLE_REPORT)
        data = resp.json()
        assert "analysis" in data


class TestSyncDirective:
    def test_directive_returns_200(self, client):
        directive = {
            "target": "popeyes",
            "type": "alert",
            "message": "형틀3팀 생산성 하락 분석 요청",
            "priority": "high",
        }
        resp = client.post("/api/sync/directive", json=directive)
        assert resp.status_code == 200

    def test_directive_invalid_priority_rejected(self, client):
        directive = {
            "target": "popeyes",
            "type": "alert",
            "message": "test",
            "priority": "invalid",
        }
        resp = client.post("/api/sync/directive", json=directive)
        assert resp.status_code == 422


class TestSyncStatus:
    def test_status_returns_brains_key(self, client):
        resp = client.get("/api/sync/status")
        assert resp.status_code == 200
        assert "brains" in resp.json()

    def test_status_after_report(self, client):
        client.post("/api/sync/report", json=SAMPLE_REPORT)
        data = client.get("/api/sync/status").json()
        brain = data["brains"].get("popeyes", {})
        assert brain.get("status") == "ok"
        assert "last_report" in brain
