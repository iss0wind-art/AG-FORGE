"""
run.py 기동 스크립트 테스트
"""
from __future__ import annotations
import os
import pytest
from unittest.mock import patch, MagicMock
from run import validate_env, print_access_info, open_zrok_tunnel


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


class TestOpenZrokTunnel:

    def test_returns_public_url(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Access server at: https://abc123.share.zrok.io"
        mock_result.stderr = ""

        mock_status = MagicMock()
        mock_status.returncode = 0

        with patch("subprocess.run", side_effect=[mock_status, mock_result]):
            url = open_zrok_tunnel(8000)

        assert url == "https://abc123.share.zrok.io"

    def test_raises_when_zrok_not_installed(self):
        import subprocess
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="ZROK 명령어를 찾을 수 없습니다"):
                open_zrok_tunnel(8000)

    def test_raises_when_not_authenticated(self):
        mock_status = MagicMock()
        mock_status.returncode = 1

        with patch("subprocess.run", return_value=mock_status):
            with pytest.raises(RuntimeError, match="ZROK 미인증"):
                open_zrok_tunnel(8000)

    def test_raises_when_tunnel_fails(self):
        mock_status = MagicMock()
        mock_status.returncode = 0

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "tunnel error"

        with patch("subprocess.run", side_effect=[mock_status, mock_result]):
            with pytest.raises(RuntimeError, match="ZROK 터널 실패"):
                open_zrok_tunnel(8000)


class TestPrintAccessInfo:

    def test_prints_local_url(self, capsys):
        print_access_info("http://localhost:8000", 8000)
        out = capsys.readouterr().out
        assert "localhost:8000" in out

    def test_prints_public_url_when_different(self, capsys):
        print_access_info("https://abc.share.zrok.io", 8000)
        out = capsys.readouterr().out
        assert "abc.share.zrok.io" in out
        assert "ZROK" in out

    def test_no_public_when_local(self, capsys):
        print_access_info("http://localhost:8000", 8000)
        out = capsys.readouterr().out
        assert "ZROK 터널 활성화" not in out
