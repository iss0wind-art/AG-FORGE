"""
피지수 망각 관리자 — Hot Tier(Obsidian) → Cold Tier(ChromaDB) 이관
망각 기준: 시간(LRU) + 결과 기반 소급 평가
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import frontmatter  # pip install python-frontmatter

VAULT_ROOT = Path(__file__).parent.parent
WIKI_DIR = VAULT_ROOT / "wiki"
WORKING_DIR = VAULT_ROOT / "working_memory"
LTM_DIR = VAULT_ROOT / "long_term_memory"
GOD_NODES_DIR = VAULT_ROOT / "god_nodes"
CHRONICLE_DIR = VAULT_ROOT / "chronicle"
LOG_FILE = VAULT_ROOT / "wiki" / "log.md"

FORGET_DAYS = 7          # LRU 기준일
FORGET_IMPORTANCE = 0.3  # 중요도 임계값
PROMOTE_REFS = 3         # 장기기억 승격 참조 횟수
PROMOTE_IMPORTANCE = 0.7 # 장기기억 승격 중요도


def is_god_node(path: Path) -> bool:
    return GOD_NODES_DIR in path.parents or path.parent == GOD_NODES_DIR


def get_importance(post) -> float:
    """YAML frontmatter의 importance 필드 읽기. 없으면 0.5 기본값."""
    return float(post.metadata.get("importance", 0.5))


def get_ref_count(post) -> int:
    return int(post.metadata.get("ref_count", 0))


def get_outcome_score(post) -> float:
    """결과 기반 소급 평가 점수. chronicle에서 참조된 횟수 기반."""
    return float(post.metadata.get("outcome_score", 0.0))


def days_since_access(path: Path) -> int:
    stat = path.stat()
    last = datetime.fromtimestamp(stat.st_mtime)
    return (datetime.now() - last).days


def should_forget(path: Path, post) -> bool:
    if is_god_node(path):
        return False
    if post.metadata.get("immutable"):
        return False

    days = days_since_access(path)
    importance = get_importance(post)
    outcome = get_outcome_score(post)

    # 결과 기반 소급 평가 — 좋은 결과에 기여한 노트는 망각 보호
    if outcome > 0.5:
        return False

    return days > FORGET_DAYS and importance < FORGET_IMPORTANCE


def should_promote(path: Path, post) -> bool:
    if LTM_DIR in path.parents:
        return False  # 이미 승격됨
    if is_god_node(path):
        return False

    refs = get_ref_count(post)
    importance = get_importance(post)
    outcome = get_outcome_score(post)

    return refs >= PROMOTE_REFS or importance >= PROMOTE_IMPORTANCE or outcome >= 0.7


def append_log(message: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n- [{now}] {message}")


def move_to_cold_tier(path: Path):
    """ChromaDB Cold Tier로 이관"""
    from cold_tier import ingest
    ingest(path)
    archive_dir = VAULT_ROOT / "archive"
    archive_dir.mkdir(exist_ok=True)
    dest = archive_dir / path.name
    shutil.move(str(path), str(dest))
    append_log(f"망각(Cold Tier 이관): {path.name}")
    print(f"  [망각] {path.name} → ChromaDB + archive/")


def promote_to_ltm(path: Path):
    dest = LTM_DIR / path.name
    shutil.move(str(path), str(dest))
    append_log(f"승격(LTM): {path.name}")
    print(f"  [승격] {path.name} → long_term_memory/")


def run():
    print(f"[피지수 망각 관리자] {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Vault: {VAULT_ROOT}")

    targets = list(WIKI_DIR.glob("**/*.md")) + list(WORKING_DIR.glob("**/*.md"))
    forgotten, promoted = 0, 0

    for path in targets:
        if path.name in ("index.md", "log.md", "CLAUDE.md"):
            continue
        try:
            post = frontmatter.load(str(path))
        except Exception:
            continue

        if should_promote(path, post):
            promote_to_ltm(path)
            promoted += 1
        elif should_forget(path, post):
            move_to_cold_tier(path)
            forgotten += 1

    print(f"\n완료 — 승격: {promoted}개 / 망각: {forgotten}개")
    append_log(f"망각 사이클 완료 — 승격 {promoted}건, 망각 {forgotten}건")


if __name__ == "__main__":
    run()
