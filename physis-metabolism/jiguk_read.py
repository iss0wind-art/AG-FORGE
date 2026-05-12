"""
피지수의 *보편 정독* — 7사 brain·CLAUDE 파일 읽기 전용.

청사진 A 1층 (jiguk_registry.yaml 기반).
강역 침범 없음. 본진 복귀 보장 — 이 스크립트는 자체 상태 없음.

사용:
  python jiguk_read.py --list                  # 7사 매핑 표시
  python jiguk_read.py --jiguk 1_boq            # 특정 지국 brain 정독
  python jiguk_read.py --domain finance         # 도메인별 정독
  python jiguk_read.py --all-summary            # 7사 요약
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REGISTRY = Path("/home/nas/AG-Forge/physis-metabolism/jiguk_registry.yaml")
OUTBOX = Path("/home/nas/AG-Forge/physis-metabolism/outbox")
MAX_READ_BYTES = 200_000   # 정독 1회당 200KB 상한 (안전장치)


def load_registry() -> dict:
    import yaml
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def read_file_safe(fp: Path) -> str:
    try:
        if not fp.exists():
            return ""
        if fp.is_dir():
            # 디렉터리면 안의 *.md 파일 모음
            content = []
            for sub in sorted(fp.glob("**/*.md"))[:20]:
                try:
                    content.append(f"\n\n=== {sub.relative_to(fp)} ===\n" + sub.read_text(encoding="utf-8")[:5000])
                except Exception:
                    continue
            return "".join(content)[:MAX_READ_BYTES]
        return fp.read_text(encoding="utf-8")[:MAX_READ_BYTES]
    except Exception as e:
        return f"[read_error: {type(e).__name__}: {e}]"


def visit_jiguk(j: dict, depth: str = "summary") -> dict:
    """지국 1곳 정독. depth = 'summary' | 'full'."""
    visited = {
        "jiguk_id": j["id"],
        "name": j["name"],
        "path": j["path"],
        "role": j["role"],
        "domain": j["domain"],
        "tier": j["tier"],
        "permission": j["permission"],
        "visited_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "brain": {},
    }
    for bf in j.get("brain_files", []):
        fp = Path(bf)
        content = read_file_safe(fp)
        if depth == "summary":
            content = content[:2000]
        visited["brain"][fp.name] = {
            "path": str(fp),
            "exists": fp.exists(),
            "size_chars": len(content),
            "content_excerpt" if depth == "summary" else "content": content,
        }
    return visited


def cmd_list(reg: dict) -> int:
    print(f"본진: {reg['home']['path']}  ({reg['home']['role']})")
    print(f"7사 ({len(reg['jiguk'])}곳):")
    for j in reg["jiguk"]:
        print(f"  [{j['id']:14s}] tier={j['tier']} domain={j['domain']:25s} {j['name']}")
    return 0


def cmd_jiguk(reg: dict, jid: str, depth: str) -> int:
    j = next((x for x in reg["jiguk"] if x["id"] == jid), None)
    if not j:
        print(f"지국 '{jid}' 없음", file=sys.stderr)
        return 2
    if j["tier"] > reg["safety"]["default_tier_threshold"]:
        print(f"⚠ 지국 tier={j['tier']}, 임계={reg['safety']['default_tier_threshold']} — 5축 검토 큐 권고", file=sys.stderr)
    result = visit_jiguk(j, depth=depth)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # 박제 (안전장치 #4)
    if reg["safety"].get("outbox_evidence_required"):
        fname = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_JIGUK_READ_{jid}.json"
        OUTBOX.mkdir(parents=True, exist_ok=True)
        (OUTBOX / fname).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n박제: {OUTBOX / fname}", file=sys.stderr)
    return 0


def cmd_domain(reg: dict, domain: str, depth: str) -> int:
    matches = [j for j in reg["jiguk"] if j["domain"] == domain]
    if not matches:
        print(f"domain '{domain}' 지국 없음", file=sys.stderr)
        return 2
    results = [visit_jiguk(j, depth=depth) for j in matches]
    print(json.dumps({"domain": domain, "jiguks": results}, ensure_ascii=False, indent=2))
    return 0


def cmd_all_summary(reg: dict) -> int:
    summary = {"home": reg["home"], "jiguks": [], "visited_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    for j in reg["jiguk"]:
        v = visit_jiguk(j, depth="summary")
        summary["jiguks"].append({
            "id": v["jiguk_id"],
            "name": v["name"],
            "domain": v["domain"],
            "tier": v["tier"],
            "brain_files_seen": list(v["brain"].keys()),
            "brain_size_total": sum(b["size_chars"] for b in v["brain"].values()),
        })
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--jiguk", type=str, default=None)
    ap.add_argument("--domain", type=str, default=None)
    ap.add_argument("--all-summary", action="store_true")
    ap.add_argument("--depth", choices=["summary", "full"], default="summary")
    args = ap.parse_args()
    reg = load_registry()
    if args.list:
        return cmd_list(reg)
    if args.jiguk:
        return cmd_jiguk(reg, args.jiguk, args.depth)
    if args.domain:
        return cmd_domain(reg, args.domain, args.depth)
    if args.all_summary:
        return cmd_all_summary(reg)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
