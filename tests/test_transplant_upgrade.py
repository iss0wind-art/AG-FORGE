"""transplant.py 고도화 테스트"""
import pytest
import json
from pathlib import Path
from scripts.transplant import transplant


@pytest.fixture
def tmp_target(tmp_path):
    return str(tmp_path)


class TestTransplantUpgrade:
    def test_basic_transplant_creates_brain_dir(self, tmp_target):
        transplant(tmp_target)
        assert (Path(tmp_target) / ".brain").exists()

    def test_transplant_with_role_creates_config(self, tmp_target):
        transplant(tmp_target, role="field_brain")
        config_path = Path(tmp_target) / ".brain" / "physis_config.json"
        assert config_path.exists()

    def test_config_contains_role(self, tmp_target):
        transplant(tmp_target, role="field_brain")
        config = json.loads((Path(tmp_target) / ".brain" / "physis_config.json").read_text())
        assert config["role"] == "field_brain"

    def test_config_contains_master_url(self, tmp_target):
        transplant(tmp_target, role="field_brain", master="http://ag-forge:8000")
        config = json.loads((Path(tmp_target) / ".brain" / "physis_config.json").read_text())
        assert config["master_url"] == "http://ag-forge:8000"

    def test_creates_run_daily_report_script(self, tmp_target):
        transplant(tmp_target, role="field_brain")
        assert (Path(tmp_target) / "scripts" / "run_daily_report.py").exists()

    def test_default_role_is_field_brain(self, tmp_target):
        transplant(tmp_target, role="field_brain")
        config = json.loads((Path(tmp_target) / ".brain" / "physis_config.json").read_text())
        assert config["role"] == "field_brain"
