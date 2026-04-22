"""
관측성 레이어 테스트 — TDD RED 단계
"""
from __future__ import annotations
import json
import pytest
from pathlib import Path
from scripts.brain_loader import BrainResponse
from scripts.observability import (
    calculate_cost,
    record_trace,
    append_log,
    summarize_session,
    TraceRecord,
    PRICING,
)


# ──────────────────────────────────────────
# calculate_cost 테스트
# ──────────────────────────────────────────

class TestCalculateCost:

    def test_sonnet_pro_cost(self):
        # gemini-2.5-pro: input $1.25/M, output $10.00/M
        cost = calculate_cost("gemini-2.5-pro", input_tokens=1_000_000, output_tokens=1_000_000)
        assert abs(cost - 11.25) < 0.001

    def test_flash_is_cheaper_than_pro(self):
        cost_pro   = calculate_cost("gemini-2.5-pro",   input_tokens=10_000, output_tokens=1_000)
        cost_flash = calculate_cost("gemini-2.0-flash", input_tokens=10_000, output_tokens=1_000)
        assert cost_flash < cost_pro

    def test_zero_tokens_returns_zero(self):
        assert calculate_cost("gemini-2.5-pro", 0, 0) == 0.0

    def test_unknown_model_raises(self):
        with pytest.raises(KeyError):
            calculate_cost("unknown-model", 1000, 1000)

    def test_small_request_cost(self):
        # 1000 input + 500 output with gemini-2.0-flash
        # input: 1000/1M * 0.075 = 0.000075
        # output: 500/1M * 0.30 = 0.00015
        cost = calculate_cost("gemini-2.0-flash", input_tokens=1_000, output_tokens=500)
        assert abs(cost - 0.000225) < 0.000001


# ──────────────────────────────────────────
# record_trace 테스트
# ──────────────────────────────────────────

class TestRecordTrace:

    def _make_response(self, model="gemini-2.5-pro", tokens=500, cache_hit=False):
        return BrainResponse(
            text="테스트 응답",
            model=model,
            task_type="code",
            tokens_used=tokens,
            cache_hit=cache_hit,
        )

    def test_returns_trace_record(self):
        resp = self._make_response()
        record = record_trace(resp, "테스트 작업", ["brain.md", "logic_rb.md"])
        assert isinstance(record, TraceRecord)

    def test_task_is_preserved(self):
        resp = self._make_response()
        record = record_trace(resp, "알고리즘 최적화", [])
        assert record.task == "알고리즘 최적화"

    def test_model_is_preserved(self):
        resp = self._make_response(model="gemini-2.0-flash")
        record = record_trace(resp, "UI 수정", [])
        assert record.model == "gemini-2.0-flash"

    def test_layers_are_preserved(self):
        resp = self._make_response()
        layers = ["brain.md", "logic_rb.md"]
        record = record_trace(resp, "작업", layers)
        assert record.layers_loaded == layers

    def test_cost_is_calculated(self):
        resp = self._make_response(model="gemini-2.5-pro", tokens=1000)
        record = record_trace(resp, "작업", [])
        assert record.cost_usd > 0

    def test_cache_hit_is_preserved(self):
        resp = self._make_response(cache_hit=True)
        record = record_trace(resp, "작업", [])
        assert record.cache_hit is True

    def test_timestamp_is_set(self):
        resp = self._make_response()
        record = record_trace(resp, "작업", [])
        assert len(record.timestamp) > 0


# ──────────────────────────────────────────
# append_log 테스트
# ──────────────────────────────────────────

class TestAppendLog:

    def test_creates_log_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.observability.LOG_PATH", tmp_path / "test.jsonl")
        record = TraceRecord(
            timestamp="2026-04-08 12:00",
            task="테스트",
            model="gemini-2.5-pro",
            task_type="code",
            tokens_used=500,
            cache_hit=False,
            cost_usd=0.001,
        )
        append_log(record)
        assert (tmp_path / "test.jsonl").exists()

    def test_log_is_valid_json(self, tmp_path, monkeypatch):
        log_path = tmp_path / "test.jsonl"
        monkeypatch.setattr("scripts.observability.LOG_PATH", log_path)
        record = TraceRecord(
            timestamp="2026-04-08 12:00",
            task="테스트",
            model="gemini-2.0-flash",
            task_type="ui",
            tokens_used=100,
            cache_hit=True,
            cost_usd=0.0001,
        )
        append_log(record)
        line = log_path.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert data["model"] == "gemini-2.0-flash"
        assert data["cache_hit"] is True

    def test_multiple_records_appended(self, tmp_path, monkeypatch):
        log_path = tmp_path / "test.jsonl"
        monkeypatch.setattr("scripts.observability.LOG_PATH", log_path)
        for i in range(3):
            append_log(TraceRecord(
                timestamp=f"2026-04-08 12:0{i}",
                task=f"작업{i}",
                model="gemini-2.5-pro",
                task_type="code",
                tokens_used=100 * i,
                cache_hit=False,
                cost_usd=0.001 * i,
            ))
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3


# ──────────────────────────────────────────
# summarize_session 테스트
# ──────────────────────────────────────────

class TestSummarizeSession:

    def _write_log(self, path: Path, records: list[dict]) -> None:
        path.write_text(
            "\n".join(json.dumps(r) for r in records),
            encoding="utf-8"
        )

    def test_total_requests(self, tmp_path):
        log = tmp_path / "test.jsonl"
        self._write_log(log, [
            {"task": "a", "model": "gemini-2.5-pro", "tokens_used": 100, "cost_usd": 0.01, "cache_hit": False},
            {"task": "b", "model": "gemini-2.0-flash", "tokens_used": 50,  "cost_usd": 0.001, "cache_hit": True},
        ])
        summary = summarize_session(log)
        assert summary["total_requests"] == 2

    def test_total_cost(self, tmp_path):
        log = tmp_path / "test.jsonl"
        self._write_log(log, [
            {"task": "a", "model": "gemini-2.5-pro", "tokens_used": 100, "cost_usd": 0.01, "cache_hit": False},
            {"task": "b", "model": "gemini-2.5-pro", "tokens_used": 200, "cost_usd": 0.02, "cache_hit": False},
        ])
        summary = summarize_session(log)
        assert abs(summary["total_cost_usd"] - 0.03) < 0.0001

    def test_cache_hit_rate(self, tmp_path):
        log = tmp_path / "test.jsonl"
        self._write_log(log, [
            {"task": "a", "model": "gemini-2.5-pro", "tokens_used": 100, "cost_usd": 0.01, "cache_hit": True},
            {"task": "b", "model": "gemini-2.5-pro", "tokens_used": 100, "cost_usd": 0.01, "cache_hit": True},
            {"task": "c", "model": "gemini-2.5-pro", "tokens_used": 100, "cost_usd": 0.01, "cache_hit": False},
            {"task": "d", "model": "gemini-2.5-pro", "tokens_used": 100, "cost_usd": 0.01, "cache_hit": False},
        ])
        summary = summarize_session(log)
        assert summary["cache_hit_rate"] == 0.5

    def test_empty_log_returns_zeros(self, tmp_path):
        log = tmp_path / "empty.jsonl"
        log.write_text("", encoding="utf-8")
        summary = summarize_session(log)
        assert summary["total_requests"] == 0
        assert summary["total_cost_usd"] == 0.0
        assert summary["cache_hit_rate"] == 0.0
