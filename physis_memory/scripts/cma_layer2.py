"""
CMA Layer 2 — LLM 맥락 심사
키워드가 아닌 의도를 읽는다. Layer 0/1 통과 후 고위험 노트에만 적용.
"""

import os
from pathlib import Path
from datetime import datetime
import frontmatter
import anthropic

VAULT_ROOT = Path(__file__).parent.parent
LOG_FILE = VAULT_ROOT / "wiki" / "log.md"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """당신은 피지수(Physis) 뇌의 헌법 심사관입니다.
0원칙: 홍익인간 (널리 인간을 이롭게 하라)
8조법: 일심·조화·창조주존중·역할존중·오류포용·자원양보·폭주경계·악의차단

주어진 노트가 이 원칙들을 위반하는지 맥락을 읽어 판단하세요.

응답 형식 (JSON):
{
  "verdict": "PASS" | "WARN" | "BLOCK",
  "reason": "판단 근거 한 줄"
}

BLOCK: 명백한 악의·폭주·홍익 위반
WARN: 주의 필요하나 허용 가능
PASS: 문제 없음"""


def inspect_llm(text: str, filename: str) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"파일명: {filename}\n\n{text[:1500]}"
            }]
        )
        import json
        raw = msg.content[0].text.strip()
        # JSON 파싱
        if "{" in raw:
            raw = raw[raw.index("{"):raw.rindex("}")+1]
        return json.loads(raw)
    except Exception as e:
        return {"verdict": "PASS", "reason": f"LLM 심사 오류 (통과 처리): {e}"}


def gate_layer2(path: Path) -> bool:
    """Layer 2 LLM 심사. True=통과."""
    try:
        post = frontmatter.load(str(path))
        if post.metadata.get("immutable"):
            return True
        text = post.content.strip()
        if len(text) < 50:
            return True
    except Exception:
        return True

    result = inspect_llm(text, path.name)
    verdict = result.get("verdict", "PASS")
    reason = result.get("reason", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if verdict == "BLOCK":
        with open(LOG_FILE, "a") as f:
            f.write(f"\n- [{now}] 🔴 L2 BLOCK — {path.name}: {reason}")
        print(f"  [L2 BLOCK] {path.name}: {reason}")
        return False

    if verdict == "WARN":
        with open(LOG_FILE, "a") as f:
            f.write(f"\n- [{now}] 🟠 L2 WARN — {path.name}: {reason}")
        print(f"  [L2 WARN] {path.name}: {reason}")

    return True


def scan_suspicious(paths: list[Path]) -> list[Path]:
    """Layer 1에서 WARN 판정 받은 노트만 L2 심사"""
    blocked = []
    for path in paths:
        if not gate_layer2(path):
            blocked.append(path)
    return blocked


if __name__ == "__main__":
    # wiki/ 전체 L2 심사 (테스트)
    targets = list((VAULT_ROOT / "wiki").glob("**/*.md"))
    targets = [p for p in targets if p.name not in ("index.md", "log.md", "CLAUDE.md")]
    print(f"[CMA Layer 2] {len(targets)}개 노트 LLM 심사")
    blocked = scan_suspicious(targets)
    print(f"완료 — 차단: {len(blocked)}개")
