"""
피지수 기억 승격 관리자 — 결과 기반 소급 평가
단재 Chronicle을 읽어 결과 기여도를 역산, outcome_score 업데이트
"""

import re
from pathlib import Path
from datetime import datetime
import frontmatter

VAULT_ROOT = Path(__file__).parent.parent
WIKI_DIR = VAULT_ROOT / "wiki"
CHRONICLE_DIR = VAULT_ROOT / "chronicle"
LOG_FILE = VAULT_ROOT / "wiki" / "log.md"


def extract_wikilinks(text: str) -> list[str]:
    return re.findall(r'\[\[([^\]]+)\]\]', text)


def build_reference_map() -> dict[str, int]:
    """전체 vault에서 노트별 참조 횟수 계산"""
    ref_map: dict[str, int] = {}
    all_md = list(VAULT_ROOT.glob("**/*.md"))
    for path in all_md:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for link in extract_wikilinks(text):
            key = link.split("|")[0].strip()
            ref_map[key] = ref_map.get(key, 0) + 1
    return ref_map


def build_outcome_map() -> dict[str, float]:
    """단재 Chronicle에서 결과 기여도 역산"""
    outcome_map: dict[str, float] = {}
    for path in CHRONICLE_DIR.glob("**/*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        # chronicle에서 언급된 노트는 결과에 기여한 것으로 판정
        for link in extract_wikilinks(text):
            key = link.split("|")[0].strip()
            outcome_map[key] = min(1.0, outcome_map.get(key, 0.0) + 0.2)
    return outcome_map


def update_scores():
    ref_map = build_reference_map()
    outcome_map = build_outcome_map()
    updated = 0

    for path in VAULT_ROOT.glob("**/*.md"):
        if path.name in ("index.md", "log.md", "CLAUDE.md"):
            continue
        try:
            post = frontmatter.load(str(path))
        except Exception:
            continue

        stem = path.stem
        new_refs = ref_map.get(stem, 0)
        new_outcome = outcome_map.get(stem, post.metadata.get("outcome_score", 0.0))

        changed = (
            post.metadata.get("ref_count") != new_refs or
            abs(float(post.metadata.get("outcome_score", 0.0)) - new_outcome) > 0.01
        )

        if changed:
            post.metadata["ref_count"] = new_refs
            post.metadata["outcome_score"] = round(new_outcome, 3)
            with open(path, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))
            updated += 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n- [{now}] 소급 평가 완료 — {updated}개 노트 점수 갱신")
    print(f"[소급 평가] {updated}개 노트 ref_count·outcome_score 갱신")


if __name__ == "__main__":
    update_scores()
