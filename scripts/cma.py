"""
CMA 헌법적 메모리 저장 파이프라인 — cma.py
Constitutional Memory Architecture: 기억 저장 시 헌법 필터링.

cma_gate.py (AI 출력 검증) 와 역할이 다르다:
  - cma_gate.py : AI 출력이 8조 금법 위반인지 판단 (출력 검증)
  - cma.py      : 새 기억을 ChromaDB에 저장할 때 헌법 필터링 (기억 저장 필터)

저장 파이프라인:
  1단: hard_constraint_check  — layer0_check BLOCK 위반이면 즉시 거부
  2단: titans_memory          — store_memory (surprise 계산 + merge/저장 처리 포함)
  3단: audit_trail 기록       — IEEE 7001 준수 append-only JSONL
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from scripts.cma_gate import ViolationLevel, layer0_check
from scripts.embedding import ChromaVectorIndex, build_default_embedder
from scripts.titans_memory import store_memory

# ── 기본 상수 ─────────────────────────────────────────────────────────────────

DEFAULT_AUDIT_PATH = Path(__file__).parent.parent / ".cma_audit.jsonl"


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────


def _write_audit(
    path: Path | None,
    content: str,
    category: str,
    status: str,
    reason: str,
) -> None:
    """IEEE 7001 준수 감사 추적 — append-only JSONL."""
    target = path if path is not None else DEFAULT_AUDIT_PATH
    entry = {
        "timestamp": datetime.now().isoformat(),
        "category": category,
        "content_preview": content[:100],
        "status": status,
        "reason": reason,
    }
    try:
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        import sys
        print(f"[cma] audit 기록 실패: {exc}", file=sys.stderr)


# ── 공개 API ──────────────────────────────────────────────────────────────────


def memory_store(
    content: str,
    category: str,
    index: ChromaVectorIndex,
    embedder,
    audit_path: Path | None = None,
) -> dict:
    """
    CMA 헌법적 메모리 저장 파이프라인.

    1단: layer0_check — BLOCK 위반이면 즉시 거부
    2단: store_memory — surprise 계산 후 merge 또는 신규 저장
    3단: audit_trail 기록

    Returns:
        {"status": "stored" | "rejected" | "merged", "reason": str}
    """
    # 1단 — 헌법 게이트 (Layer 0 BLOCK 패턴)
    violation = layer0_check(content, content)
    if violation is not None and violation.level == ViolationLevel.BLOCK:
        _write_audit(audit_path, content, category, "rejected", violation.violated_code)
        return {"status": "rejected", "reason": violation.violated_code}

    # 2단 — Surprise 체크 + 저장 (store_memory 내부에서 처리)
    stored = store_memory(content, category, index, embedder)
    status = "stored" if stored else "merged"
    reason = "surprise threshold 초과: 신규 저장" if stored else "기존 기억과 유사: merge(reinforce)"

    # 3단 — 감사 로그
    _write_audit(audit_path, content, category, status, reason)

    return {"status": status, "reason": reason}


def get_audit_log(
    audit_path: Path | None = None,
    last_n: int = 50,
) -> list[dict]:
    """감사 로그 최근 N개 조회."""
    target = audit_path if audit_path is not None else DEFAULT_AUDIT_PATH
    if not target.exists():
        return []

    entries: list[dict] = []
    try:
        for line in target.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []

    return entries[-last_n:]


def build_cma_store(
    persist_path: str | None = None,
) -> tuple[ChromaVectorIndex, object]:
    """기본 설정으로 index + embedder 쌍을 생성한다."""
    idx = ChromaVectorIndex(persist_path or "d:/Git/AG-Forge/library/vector_db")
    emb = build_default_embedder()
    return idx, emb
