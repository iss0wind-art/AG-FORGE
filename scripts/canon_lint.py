"""
canon_lint.py — canon.yaml과 brain_*.md 문서 간 일관성 검증

용도: brain 문서가 canon.yaml과 어긋나면 경고/차단.
실행: python scripts/canon_lint.py [--strict]

종료 코드:
    0 = 모든 검증 통과
    1 = 1개 이상의 위반 발견
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
from typing import Iterable

# Windows 콘솔 cp949 → UTF-8 강제
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

try:
    import yaml
except ImportError:
    print("[canon_lint] PyYAML 필요: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


PROJECT_ROOT = Path(__file__).parent.parent
CANON_PATH = PROJECT_ROOT / "canon.yaml"

BRAIN_FILES = [
    "brain.md",
    "brain_architecture.md",
    "brain_intuition.md",
    "brain_legal_patent.md",
    "brain_master_architecture.md",
    "brain_personality.md",
    "brain_philosophy.md",
    "brain_sync_protocol.md",
    "brain_task_log.md",
    "brain_transplant_strategy.md",
    ".brain/physis.md",
    "CLAUDE.md",
]


class Violation:
    def __init__(self, file: str, message: str, severity: str = "error"):
        self.file = file
        self.message = message
        self.severity = severity

    def __str__(self) -> str:
        icon = "❌" if self.severity == "error" else "⚠️"
        return f"{icon} [{self.file}] {self.message}"


def load_canon() -> dict:
    if not CANON_PATH.exists():
        print(f"[canon_lint] canon.yaml 없음: {CANON_PATH}", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(CANON_PATH.read_text(encoding="utf-8"))


def read_brain_file(name: str) -> str | None:
    path = PROJECT_ROOT / name
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# 검증 규칙
# ──────────────────────────────────────────────────────────────────────────────

def _is_in_dangun_context(content: str, match_pos: int, window: int = 200) -> bool:
    """매치 위치 주변에 단군/DREAM_FAC 표기가 있으면 단군 비교 컨텍스트로 간주."""
    start = max(0, match_pos - window)
    end = min(len(content), match_pos + window)
    nearby = content[start:end]
    return bool(re.search(r"단군|DREAM_FAC", nearby, re.IGNORECASE))


def check_layer_count(canon: dict, files: dict[str, str]) -> Iterable[Violation]:
    """레이어 개수가 canon과 일치하는가. 단군 비교 컨텍스트는 예외로 인정."""
    # "5계층" 또는 "13체" 같은 비정합 표기 탐지
    forbidden_patterns = [
        (r"\b5\s*계층\b", "5계층 표기 발견 — canon은 6계층 (Physis 포함)"),
        (r"\b13\s*체\b", "13체 표기 발견 — 단군 시스템 표현 (단군 비교 컨텍스트가 아니면 부적합)"),
        (r"5\s*개\s*의\s*기능적\s*뇌(?!.*Layer\s*1~5)", "'5개 기능적 뇌' 표현 — Layer 범위 명시 없음 (혼동 유발)"),
    ]
    for fname, content in files.items():
        if content is None:
            continue
        for pattern, msg in forbidden_patterns:
            for m in re.finditer(pattern, content):
                # 13체 표기는 단군 컨텍스트면 OK
                if "13" in pattern and _is_in_dangun_context(content, m.start()):
                    continue
                yield Violation(fname, msg, "warning")
                break  # 같은 패턴은 파일당 1회만 보고


def check_persona_count(canon: dict, files: dict[str, str]) -> Iterable[Violation]:
    """페르소나 개수가 canon(=4)과 일치하는가."""
    forbidden_patterns = [
        (r"5\s*대\s*페르소나", "'5대 페르소나' 표기 — 감정 차원은 페르소나 아님 (4 + 횡단 차원)"),
        (r"5명\s*의\s*페르소나", "'5명의 페르소나' 표기 — canon은 4명"),
    ]
    for fname, content in files.items():
        if content is None:
            continue
        for pattern, msg in forbidden_patterns:
            if re.search(pattern, content):
                yield Violation(fname, msg, "warning")


def check_status_drift(canon: dict, files: dict[str, str]) -> Iterable[Violation]:
    """완료된 컴포넌트가 '진행 중/대기 중'으로 표기되었는가."""
    components = canon.get("components", {})

    # hybrid_merge는 completed → "구축 중" 표기 금지
    if components.get("hybrid_merge", {}).get("state") == "completed":
        for fname, content in files.items():
            if content is None:
                continue
            if "구축 중" in content and "하이브리드" in content:
                yield Violation(
                    fname,
                    "하이브리드 머지는 completed (canon)인데 '구축 중' 표기 발견",
                    "warning",
                )

    # hard_gate는 connected → "미연결" 표기 금지
    if components.get("hard_gate", {}).get("state") == "connected":
        for fname, content in files.items():
            if content is None:
                continue
            if re.search(r"hard.{0,3}gate.{0,15}미연결|hard.{0,3}gate.{0,15}호출.{0,5}안", content, re.IGNORECASE):
                yield Violation(
                    fname,
                    "hard_gate는 connected (canon)인데 '미연결' 표기 발견",
                    "error",
                )


def check_dead_references(canon: dict, files: dict[str, str]) -> Iterable[Violation]:
    """문서에 언급된 경로/스크립트가 실재하는가."""
    # 실재 검증할 대표 경로들
    declared_paths = [
        ("scripts/agent_graph.py", "scripts/agent_graph.py"),
        ("scripts/transplant.py", "scripts/transplant.py"),
        ("scripts/life_cycle_manager.py", "scripts/life_cycle_manager.py"),
        ("server/sync_api.py", "server/sync_api.py"),
        ("CONSTITUTION.md", "CONSTITUTION.md"),
        ("canon.yaml", "canon.yaml"),
    ]
    for label, rel_path in declared_paths:
        full = PROJECT_ROOT / rel_path
        if not full.exists():
            yield Violation(
                "canon.yaml",
                f"canon이 참조하는 경로 누락: {rel_path}",
                "error",
            )

    # scripts/brain/ 잘못된 경로 언급 탐지
    for fname, content in files.items():
        if content is None:
            continue
        if "scripts/brain/" in content:
            yield Violation(
                fname,
                "'scripts/brain/' 경로 언급 — 실제 경로는 'scripts/' 직속",
                "error",
            )


def check_v3_aspirational_claims(canon: dict, files: dict[str, str]) -> Iterable[Violation]:
    """V3 활성화 상태 거짓말 탐지. 부정/미래 표현 컨텍스트는 예외."""
    v3_state = canon.get("components", {}).get("v3_mortality", {}).get("state")
    if v3_state != "fields_defined_inactive":
        return

    NEGATION_NEAR = re.compile(
        r"미연결|미활성|미구현|예정|승인\s*(후|필수|대기|필요)|대기|"
        r"활성화\s*(는|시|후|예정|후에)|활성화\s+미",
        re.IGNORECASE,
    )

    for fname, content in files.items():
        if content is None:
            continue
        for m in re.finditer(r"V3.{0,30}(활성|operational|작동\s*중|enabled)", content, re.IGNORECASE):
            # 같은 줄 추출
            line_start = content.rfind("\n", 0, m.start()) + 1
            line_end = content.find("\n", m.end())
            if line_end == -1:
                line_end = len(content)
            line = content[line_start:line_end]

            # 같은 줄에 미완 체크박스 [ ] 또는 [/] 있으면 미래 시제로 인정
            if re.search(r"\[\s*[/ ]\s*\]", line):
                continue

            # 주변(±100자)에 부정/미래 표현이 있으면 OK
            start = max(0, m.start() - 100)
            end = min(len(content), m.end() + 100)
            nearby = content[start:end]
            if NEGATION_NEAR.search(nearby):
                continue

            yield Violation(
                fname,
                f"V3 Mortality는 {v3_state} (canon)인데 활성/작동 표기 발견 (위치 ~line {content[:m.start()].count(chr(10))+1})",
                "warning",
            )
            break  # 파일당 1회만 보고


# ──────────────────────────────────────────────────────────────────────────────
# 메인 진입점
# ──────────────────────────────────────────────────────────────────────────────

def run_lint(strict: bool = False) -> int:
    canon = load_canon()
    files = {name: read_brain_file(name) for name in BRAIN_FILES}

    missing = [name for name, content in files.items() if content is None]
    if missing:
        print("[canon_lint] 누락된 brain 파일:")
        for m in missing:
            print(f"  - {m}")

    violations: list[Violation] = []
    for check in (
        check_layer_count,
        check_persona_count,
        check_status_drift,
        check_dead_references,
        check_v3_aspirational_claims,
    ):
        violations.extend(check(canon, files))

    if not violations:
        print("[canon_lint] OK — canon.yaml과 brain 문서 일관성 통과")
        return 0

    errors = [v for v in violations if v.severity == "error"]
    warnings = [v for v in violations if v.severity == "warning"]

    print(f"[canon_lint] {len(errors)}개 error, {len(warnings)}개 warning 발견:\n")
    for v in violations:
        print(f"  {v}")

    # strict 모드면 warning도 실패. 기본은 error만 실패.
    if errors or (strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    strict = "--strict" in sys.argv
    sys.exit(run_lint(strict=strict))
