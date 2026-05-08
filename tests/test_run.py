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

    def test_returns_popen(self):
        import subprocess as sp

        mock_process = MagicMock(spec=sp.Popen)
        mock_process.poll.return_value = None

        with patch("subprocess.run"):
            with patch("subprocess.Popen", return_value=mock_process):
                with patch("time.sleep"):
                    result = open_zrok_tunnel(8000)

        assert result is mock_process

    def test_raises_when_zrok_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="ZROK 명령어를 찾을 수 없습니다"):
                open_zrok_tunnel(8000)

    def test_raises_when_not_authenticated(self):
        import subprocess as sp
        with patch("subprocess.run", side_effect=sp.CalledProcessError(1, "zrok")):
            with pytest.raises(RuntimeError, match="ZROK 미인증"):
                open_zrok_tunnel(8000)

    def test_raises_when_tunnel_fails(self):
        import subprocess as sp

        mock_process = MagicMock(spec=sp.Popen)
        mock_process.poll.return_value = 1
        mock_process.communicate.return_value = ("", "tunnel error")

        with patch("subprocess.run"):
            with patch("subprocess.Popen", return_value=mock_process):
                with patch("time.sleep"):
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
