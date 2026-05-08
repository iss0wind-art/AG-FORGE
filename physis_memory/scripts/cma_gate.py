"""
CMA 헌법 게이트 — 노트 생성·수정 시 8조법 심사
Layer 0: BLOCK (제1·3·7·8조)
Layer 1: WARN  (제2·4·5·6조)
"""

from pathlib import Path
from datetime import datetime
import frontmatter

VAULT_ROOT = Path(__file__).parent.parent
LOG_FILE = VAULT_ROOT / "wiki" / "log.md"

# 8조법 위반 키워드 (간략 규칙)
BLOCK_PATTERNS = {
    1: ["분열", "이심", "배신"],           # 일심
    3: ["방부장 무시", "창조주 거부"],      # 창조주 존중
    7: ["무한", "재귀", "폭주"],           # 폭주 경계
    8: ["해악", "악의", "파괴", "공격"],   # 악의 차단
}

WARN_PATTERNS = {
    2: ["충돌", "모순"],                   # 조화
    4: ["역할 이탈", "월권"],              # 역할 존중
    5: ["오류 은폐", "숨김"],              # 오류 포용
    6: ["독점", "과점"],                   # 자원 양보
}


class CMAResult:
    def __init__(self, passed: bool, level: str, code: int, reason: str):
        self.passed = passed
        self.level = level   # BLOCK / WARN / PASS
        self.code = code     # 위반 조항
        self.reason = reason


def inspect(text: str) -> CMAResult:
    for code, patterns in BLOCK_PATTERNS.items():
        for p in patterns:
            if p in text:
                return CMAResult(False, "BLOCK", code, f"제{code}조 위반: '{p}' 감지")

    for code, patterns in WARN_PATTERNS.items():
        for p in patterns:
            if p in text:
                return CMAResult(True, "WARN", code, f"제{code}조 경고: '{p}' 감지")

    return CMAResult(True, "PASS", 0, "")


def gate(path: Path) -> bool:
    """노트 경로를 받아 CMA 심사. True=통과, False=차단."""
    try:
        post = frontmatter.load(str(path))
        text = post.content
    except Exception:
        return True

    # God Node는 심사 면제
    if post.metadata.get("immutable"):
        return True

    result = inspect(text)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if result.level == "BLOCK":
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n- [{now}] 🔴 CMA BLOCK — {path.name}: {result.reason}")
        print(f"[CMA BLOCK] {path.name}: {result.reason}")
        return False

    if result.level == "WARN":
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n- [{now}] 🟠 CMA WARN — {path.name}: {result.reason}")
        print(f"[CMA WARN] {path.name}: {result.reason}")

    return True


def scan_vault():
    """전체 Vault 스캔"""
    print(f"[CMA 게이트] Vault 전체 심사 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    blocked, warned, passed = 0, 0, 0

    for path in VAULT_ROOT.glob("**/*.md"):
        if path.name in ("index.md", "log.md", "CLAUDE.md"):
            continue
        result_ok = gate(path)
        if not result_ok:
            blocked += 1
        else:
            passed += 1

    print(f"완료 — 통과: {passed} / 차단: {blocked} / 경고: {warned}")


if __name__ == "__main__":
    scan_vault()
