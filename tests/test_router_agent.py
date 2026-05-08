"""
소뇌 라우터 테스트 — TDD RED 단계
모든 테스트는 구현 전에 작성되었습니다.
"""
import pytest
from scripts.router_agent import TaskType, RoutingDecision, classify_task, route, log_routing


# ──────────────────────────────────────────
# classify_task 테스트
# ──────────────────────────────────────────

class TestClassifyTask:

    def test_ui_keywords_korean(self):
        assert classify_task("버튼 색상 수정해줘") == TaskType.UI

    def test_ui_keywords_english(self):
        assert classify_task("fix the button color") == TaskType.UI

    def test_ui_design_keyword(self):
        assert classify_task("디자인 문구 바꿔줘") == TaskType.UI

    def test_code_keyword_korean(self):
        assert classify_task("이 알고리즘 최적화해줘") == TaskType.CODE

    def test_code_keyword_db(self):
        assert classify_task("DB 스키마 설계 부탁해") == TaskType.CODE

    def test_code_keyword_bug(self):
        assert classify_task("버그 수정이 필요해") == TaskType.CODE

    def test_planning_keyword_korean(self):
        assert classify_task("전략 기획 해줘") == TaskType.PLANNING

    def test_planning_keyword_english(self):
        assert classify_task("research the market") == TaskType.PLANNING

    def test_architecture_keyword(self):
        assert classify_task("전체 시스템 아키텍처 설계") == TaskType.ARCHITECTURE

    def test_architecture_tradeoff(self):
        assert classify_task("이 구조의 트레이드오프 분석") == TaskType.ARCHITECTURE

    def test_unknown_defaults_to_planning(self):
        """분류 불명확 → PLANNING 기본값"""
        assert classify_task("안녕하세요") == TaskType.PLANNING

    def test_case_insensitive(self):
        assert classify_task("Fix the UI") == TaskType.UI


# ──────────────────────────────────────────
# route 테스트
# ──────────────────────────────────────────

class TestRoute:

    def test_ui_routes_to_flash(self):
        decision = route("버튼 색상 수정")
        assert decision.model == "gemini-2.0-flash"
        assert decision.thinking_budget == 500
        assert decision.primary_layer == "emotion_ui.md"
        assert decision.task_type == TaskType.UI

    def test_code_routes_to_pro(self):
        decision = route("알고리즘 최적화")
        assert decision.model == "gemini-2.5-pro"
        assert decision.thinking_budget == 5000
        assert decision.primary_layer == "logic_rb.md"

    def test_planning_routes_to_pro(self):
        decision = route("전략 기획")
        assert decision.model == "gemini-2.5-pro"
        assert decision.thinking_budget == 2000
        assert decision.primary_layer == "brain.md"

    def test_architecture_gets_max_budget(self):
        decision = route("시스템 아키텍처 설계")
        assert decision.thinking_budget == 10000
        assert decision.primary_layer == "brain.md"

    def test_returns_frozen_dataclass(self):
        """RoutingDecision은 불변이어야 한다"""
        decision = route("버튼 수정")
        with pytest.raises((AttributeError, TypeError)):
            decision.model = "hacked"  # type: ignore


# ──────────────────────────────────────────
# log_routing 테스트
# ──────────────────────────────────────────

class TestLogRouting:

    def test_log_appends_to_judgment_md(self, tmp_path, monkeypatch):
        """judgment.md 라우팅 로그 섹션에 한 줄 추가되는지 확인"""
        judgment = tmp_path / "judgment.md"
        judgment.write_text("# 소뇌\n\n## 라우팅 로그\n\n_초기화됨._\n", encoding="utf-8")

        monkeypatch.setattr("scripts.router_agent.JUDGMENT_PATH", judgment)

        decision = RoutingDecision(
            task_type=TaskType.CODE,
            model="gemini-2.5-pro",
            thinking_budget=5000,
            primary_layer="logic_rb.md",
        )
        log_routing(decision, thinking_used=3200)

        content = judgment.read_text(encoding="utf-8")
        assert "gemini-2.5-pro" in content
        assert "3200/5000" in content
        assert "none" in content

    def test_log_with_error_flag(self, tmp_path, monkeypatch):
        judgment = tmp_path / "judgment.md"
        judgment.write_text("# 소뇌\n\n## 라우팅 로그\n\n_초기화됨._\n", encoding="utf-8")

        monkeypatch.setattr("scripts.router_agent.JUDGMENT_PATH", judgment)

        decision = RoutingDecision(
            task_type=TaskType.UI,
            model="gemini-2.0-flash",
            thinking_budget=500,
            primary_layer="emotion_ui.md",
        )
        log_routing(decision, thinking_used=480, error_flags="token_overflow")

        assert "token_overflow" in judgment.read_text(encoding="utf-8")
