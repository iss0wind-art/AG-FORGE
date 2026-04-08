"""
run.py 기동 스크립트 테스트
"""
from __future__ import annotations
import os
import pytest
from unittest.mock import patch, MagicMock
from run import validate_env, print_access_info, open_ngrok_tunnel


class TestValidateEnv:

    def test_returns_empty_when_all_set(self, monkeypatch):
        monkeypatch.setenv("AG_FORGE_API_KEY", "test-key")
        assert validate_env() == []

    def test_returns_missing_keys(self, monkeypatch):
        monkeypatch.delenv("AG_FORGE_API_KEY", raising=False)
        missing = validate_env()
        assert "AG_FORGE_API_KEY" in missing

    def test_empty_string_counts_as_missing(self, monkeypatch):
        monkeypatch.setenv("AG_FORGE_API_KEY", "")
        missing = validate_env()
        assert "AG_FORGE_API_KEY" in missing


class TestOpenNgrokTunnel:

    def test_returns_public_url(self, monkeypatch):
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://abc123.ngrok.io"

        with patch("run.ngrok") as mock_ngrok:
            mock_ngrok.connect.return_value = mock_tunnel
            url = open_ngrok_tunnel(8000)

        assert url == "https://abc123.ngrok.io"

    def test_uses_port(self, monkeypatch):
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://xyz.ngrok.io"

        with patch("run.ngrok") as mock_ngrok:
            mock_ngrok.connect.return_value = mock_tunnel
            open_ngrok_tunnel(9000)
            mock_ngrok.connect.assert_called_once_with(9000, "http")

    def test_sets_authtoken_when_provided(self, monkeypatch):
        monkeypatch.setenv("NGROK_AUTHTOKEN", "my-token")
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://test.ngrok.io"

        with patch("run.ngrok") as mock_ngrok, \
             patch("run.conf") as mock_conf:
            mock_conf.get_default.return_value = MagicMock()
            mock_ngrok.connect.return_value = mock_tunnel
            open_ngrok_tunnel(8000)
            assert mock_conf.get_default().auth_token == "my-token"


class TestPrintAccessInfo:

    def test_prints_local_url(self, capsys):
        print_access_info("http://localhost:8000", 8000)
        out = capsys.readouterr().out
        assert "localhost:8000" in out

    def test_prints_external_url_when_different(self, capsys):
        print_access_info("https://abc.ngrok.io", 8000)
        out = capsys.readouterr().out
        assert "abc.ngrok.io" in out
        assert "모바일" in out

    def test_no_external_when_local(self, capsys):
        print_access_info("http://localhost:8000", 8000)
        out = capsys.readouterr().out
        assert "모바일" not in out
