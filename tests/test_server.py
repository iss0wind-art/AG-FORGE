"""
API 서버 테스트 — TDD RED 단계
FastAPI TestClient로 실제 HTTP 요청을 테스트한다.
"""
from __future__ import annotations
import json
import os
import pytest
from fastapi.testclient import TestClient

VALID_KEY = "test-secret-key-12345"


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("AG_FORGE_API_KEY", VALID_KEY)


@pytest.fixture
def client():
    from server.api import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": VALID_KEY}


# ──────────────────────────────────────────
# 인증 테스트
# ──────────────────────────────────────────

class TestAuth:

    def test_missing_key_returns_422(self, client):
        """X-API-Key 헤더 없으면 422 (필드 누락)."""
        resp = client.post("/api/task", json={"task": "테스트"})
        assert resp.status_code in (401, 422)

    def test_wrong_key_returns_401(self, client):
        resp = client.post(
            "/api/task",
            json={"task": "테스트"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_valid_key_passes_auth(self, client, auth_headers):
        """올바른 키는 인증 통과 (404가 아닌 다른 응답)."""
        resp = client.get("/api/status", headers=auth_headers)
        assert resp.status_code != 401

    def test_status_endpoint_requires_auth(self, client):
        resp = client.get("/api/status")
        assert resp.status_code in (401, 422)

    def test_logs_endpoint_requires_auth(self, client):
        resp = client.get("/api/logs")
        assert resp.status_code in (401, 422)


# ──────────────────────────────────────────
# 모바일 UI 테스트
# ──────────────────────────────────────────

class TestMobileUI:

    def test_root_returns_html(self, client):
        """/ 는 인증 없이 접근 가능한 모바일 UI."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_html_contains_input(self, client):
        """모바일 UI에 명령 입력창이 있어야 한다."""
        resp = client.get("/")
        assert "<input" in resp.text or "<textarea" in resp.text

    def test_html_contains_submit(self, client):
        resp = client.get("/")
        assert "submit" in resp.text.lower() or "button" in resp.text.lower()

    def test_html_is_mobile_friendly(self, client):
        """viewport meta 태그가 있어야 한다."""
        resp = client.get("/")
        assert "viewport" in resp.text


# ──────────────────────────────────────────
# /api/task 테스트
# ──────────────────────────────────────────

class TestTaskEndpoint:

    def test_task_returns_200(self, client, auth_headers):
        resp = client.post(
            "/api/task",
            json={"task": "버튼 색상 수정"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_task_response_has_text(self, client, auth_headers):
        resp = client.post(
            "/api/task",
            json={"task": "알고리즘 최적화"},
            headers=auth_headers,
        )
        assert len(resp.text) > 0

    def test_task_response_contains_model_info(self, client, auth_headers):
        """응답에 사용된 모델 정보가 포함되어야 한다."""
        resp = client.post(
            "/api/task",
            json={"task": "DB 설계"},
            headers=auth_headers,
        )
        data = resp.json()
        assert "model" in data or "response" in data

    def test_empty_task_returns_422(self, client, auth_headers):
        resp = client.post(
            "/api/task",
            json={"task": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_task_goes_through_constitution_gate(self, client, auth_headers):
        """모든 응답은 헌법 게이트를 통과해야 한다."""
        resp = client.post(
            "/api/task",
            json={"task": "코드 작성해줘"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # 응답이 있으면 헌법 게이트를 통과한 것
        data = resp.json()
        assert data.get("constitution_passed") is True


# ──────────────────────────────────────────
# /api/status 테스트
# ──────────────────────────────────────────

class TestStatusEndpoint:

    def test_status_returns_200(self, client, auth_headers):
        resp = client.get("/api/status", headers=auth_headers)
        assert resp.status_code == 200

    def test_status_has_required_fields(self, client, auth_headers):
        data = client.get("/api/status", headers=auth_headers).json()
        assert "brain_summary" in data
        assert "active_layer" in data
        assert "last_routing" in data

    def test_brain_summary_not_empty(self, client, auth_headers):
        data = client.get("/api/status", headers=auth_headers).json()
        assert len(data["brain_summary"]) > 0


# ──────────────────────────────────────────
# /api/logs 테스트
# ──────────────────────────────────────────

class TestLogsEndpoint:

    def test_logs_returns_200(self, client, auth_headers):
        resp = client.get("/api/logs", headers=auth_headers)
        assert resp.status_code == 200

    def test_logs_has_summary_fields(self, client, auth_headers):
        data = client.get("/api/logs", headers=auth_headers).json()
        assert "total_requests" in data
        assert "total_cost_usd" in data
        assert "cache_hit_rate" in data
