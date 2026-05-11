"""
관측성 레이어 — observability.py
LangSmith 추적 + Gemini 비용 실시간 계산.
LangSmith 없는 환경에서도 fallback으로 동작한다.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from scripts.brain_loader import BrainResponse

# Gemini 가격표 (per 1M tokens, USD) — 2026년 4월 기준 추정치
PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-pro":   {"input": 1.25,  "output": 10.00},
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
}

LOG_PATH = Path(__file__).parent.parent / "observability_log.jsonl"


@dataclass
class TraceRecord:
    timestamp: str
    task: str
    model: str
    task_type: str
    tokens_used: int
    cache_hit: bool
    cost_usd: float
    layers_loaded: list[str] = field(default_factory=list)


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """모델과 토큰 수로 USD 비용을 계산한다."""
    prices = PRICING[model]  # 알 수 없는 모델이면 KeyError 발생
    input_cost  = (input_tokens  / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]
    return input_cost + output_cost


def record_trace(response: BrainResponse, task: str, layers_loaded: list[str]) -> TraceRecord:
    """BrainResponse를 TraceRecord로 변환한다."""
    # tokens_used를 input/output 7:3 비율로 추정 (실측 불가 시)
    estimated_input  = int(response.tokens_used * 0.7)
    estimated_output = int(response.tokens_used * 0.3)

    model = response.model
    if model not in PRICING:
        # 알 수 없는 모델은 pro 기준으로 fallback
        model = "gemini-2.5-pro"

    cost = calculate_cost(model, estimated_input, estimated_output)

    return TraceRecord(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        task=task,
        model=response.model,
        task_type=response.task_type,
        tokens_used=response.tokens_used,
        cache_hit=response.cache_hit,
        cost_usd=cost,
        layers_loaded=layers_loaded,
    )


def append_log(record: TraceRecord) -> None:
    """TraceRecord를 JSONL 형식으로 로그 파일에 추가한다."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def summarize_session(log_path: Path = LOG_PATH) -> dict:
    """로그 파일에서 세션 통계를 집계한다."""
    if not log_path.exists():
        return {"total_requests": 0, "total_cost_usd": 0.0, "cache_hit_rate": 0.0}

    try:
        raw_text = log_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw_text = log_path.read_text(encoding="cp949", errors="replace")

    lines = [l for l in raw_text.splitlines() if l.strip()]
    if not lines:
        return {"total_requests": 0, "total_cost_usd": 0.0, "cache_hit_rate": 0.0}

    records = [json.loads(l) for l in lines]
    total = len(records)
    total_cost = sum(r["cost_usd"] for r in records)
    cache_hits = sum(1 for r in records if r["cache_hit"])

    return {
        "total_requests":  total,
        "total_cost_usd":  round(total_cost, 6),
        "cache_hit_rate":  cache_hits / total,
    }
