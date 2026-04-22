"""
소뇌 (Cerebellum) — 라우터 에이전트
작업 유형을 분류하고 Gemini 모델 + Thinking Budget을 동적 할당한다.
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime

JUDGMENT_PATH = Path(__file__).parent.parent / "judgment.md"


class TaskType(Enum):
    UI = "ui"
    PLANNING = "planning"
    CODE = "code"
    ARCHITECTURE = "architecture"


@dataclass(frozen=True)
class RoutingDecision:
    task_type: TaskType
    model: str
    thinking_budget: int
    primary_layer: str


_KEYWORDS: dict[TaskType, list[str]] = {
    TaskType.ARCHITECTURE: ["아키텍처", "구조", "트레이드오프", "architect", "tradeoff", "system design"],
    TaskType.CODE:         ["코드", "함수", "db", "최적화", "알고리즘", "버그", "스키마", "algorithm", "optimize", "schema", "migration", "bug"],
    TaskType.UI:           ["수정", "색상", "버튼", "문구", "디자인", "fix", "color", "button", "ui", "copy", "style"],
    TaskType.PLANNING:     ["계획", "분석", "전략", "기획", "plan", "research", "strategy", "why", "분석"],
}

_ROUTING_TABLE: dict[TaskType, RoutingDecision] = {
    TaskType.UI: RoutingDecision(
        task_type=TaskType.UI,
        model="gemini-2.0-flash",
        thinking_budget=500,
        primary_layer="emotion_ui.md",
    ),
    TaskType.PLANNING: RoutingDecision(
        task_type=TaskType.PLANNING,
        model="gemini-2.5-pro",
        thinking_budget=2000,
        primary_layer="brain.md",
    ),
    TaskType.CODE: RoutingDecision(
        task_type=TaskType.CODE,
        model="gemini-2.5-pro",
        thinking_budget=5000,
        primary_layer="logic_rb.md",
    ),
    TaskType.ARCHITECTURE: RoutingDecision(
        task_type=TaskType.ARCHITECTURE,
        model="gemini-2.5-pro",
        thinking_budget=10000,
        primary_layer="brain.md",
    ),
}


def classify_task(task: str) -> TaskType:
    """작업 텍스트에서 TaskType을 분류한다. 우선순위: ARCHITECTURE > CODE > UI > PLANNING."""
    lower = task.lower()
    for task_type in (TaskType.ARCHITECTURE, TaskType.CODE, TaskType.UI, TaskType.PLANNING):
        if any(kw in lower for kw in _KEYWORDS[task_type]):
            return task_type
    return TaskType.PLANNING


def route(task: str) -> RoutingDecision:
    """작업을 분류하고 RoutingDecision을 반환한다."""
    return _ROUTING_TABLE[classify_task(task)]


def log_routing(decision: RoutingDecision, thinking_used: int, error_flags: str = "none") -> None:
    """judgment.md 라우팅 로그 섹션에 한 줄 기록한다."""
    log_line = (
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"{decision.task_type.value} | "
        f"{decision.model} | "
        f"{thinking_used}/{decision.thinking_budget} | "
        f"{error_flags}\n"
    )
    try:
        content = JUDGMENT_PATH.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = JUDGMENT_PATH.read_text(encoding="cp949", errors="replace")
    
    updated = content.replace("_초기화됨._\n", log_line, 1) if "_초기화됨._" in content else content + log_line
    JUDGMENT_PATH.write_text(updated, encoding="utf-8", errors="replace")
