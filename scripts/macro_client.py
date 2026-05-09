"""
macro_client.py — 피지수가 4지국(Stock-AI) 매크로 데이터를 끌어가는 클라이언트.

방부장 친명 2026-05-09 + 4지국 합의안 (docs/decisions/2026-05-09-v2-direction.md):
  · 매크로 데이터 단일창: stock-trading 수집 → 피지수가 /macro/ 호출로 소비
  · 피지수가 끌어간 데이터를 physis_finance_brain ChromaDB에 박제

호출:
  GET http://localhost:8040/macro/   ← X-Webhook-Secret 헤더 필수
  → {data: {...}, analysis: {...}}

사용:
  python3 scripts/macro_client.py --fetch          # 1회 끌어오기 + 박제
  python3 scripts/macro_client.py --fetch --quiet  # 출력 최소
  python3 scripts/macro_client.py --stats          # ChromaDB 적재 통계
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOCK_AI_ROOT = Path("/home/nas/STOCK-TRADING/Stock-Trading")
sys.path.insert(0, str(ROOT))


def _load_stock_ai_env() -> dict[str, str]:
    """Stock-AI .env에서 WEBHOOK_SECRET 가져오기."""
    env_file = STOCK_AI_ROOT / ".env"
    if not env_file.exists():
        return {}
    out = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def fetch_macro(base_url: str = "http://localhost:8040", quiet: bool = False) -> dict | None:
    """4지국 /macro/ 호출. X-Webhook-Secret 필수."""
    env = _load_stock_ai_env()
    secret = env.get("WEBHOOK_SECRET", "")
    if not secret:
        print("[오류] Stock-AI .env에 WEBHOOK_SECRET 없음")
        return None

    url = f"{base_url}/macro/"
    req = urllib.request.Request(
        url,
        headers={"X-Webhook-Secret": secret, "User-Agent": "physis-macro-client/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not quiet:
            print(f"✅ /macro/ 호출 성공: {url}")
        return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"[오류] HTTP {e.code}: {body}")
        return None
    except Exception as e:
        print(f"[오류] {type(e).__name__}: {e}")
        return None


def ingest_to_finance_brain(macro: dict, label: str | None = None) -> int:
    """매크로 데이터를 physis_finance_brain ChromaDB에 박제."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from finance_brain_ingest import get_or_create_collection

    coll = get_or_create_collection()
    ts = datetime.now()
    label = label or ts.strftime("%Y-%m-%d_%H%M%S")

    data = macro.get("data", {}) or {}
    analysis = macro.get("analysis", {}) or {}

    # 자연어 문서 (검색 가능)
    doc_parts = []
    for asset, info in data.items():
        if isinstance(info, dict):
            doc_parts.append(f"{asset}: {info}")
    for k, v in analysis.items():
        doc_parts.append(f"{k}={v}")
    doc = " | ".join(doc_parts)[:8000] or json.dumps(macro, ensure_ascii=False)[:8000]

    # 메타 (구조화 검색)
    meta = {
        "source": "stock_ai_macro_endpoint",
        "fetched_at": ts.isoformat(),
        "date": ts.strftime("%Y-%m-%d"),
        "asset_count": len(data) if isinstance(data, dict) else 0,
        "has_analysis": bool(analysis),
    }
    # 분석 핵심 메트릭만 메타에 추가 (있으면)
    if isinstance(analysis, dict):
        for k in ("market_phase", "regime", "vix_level", "fear_greed", "sentiment"):
            if k in analysis:
                meta[f"analysis_{k}"] = str(analysis[k])

    doc_id = f"macro_{label}"
    coll.add(documents=[doc], metadatas=[meta], ids=[doc_id])
    return 1


def stats():
    sys.path.insert(0, str(ROOT / "scripts"))
    from finance_brain_ingest import stats as fb_stats
    return fb_stats()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="피지수 매크로 클라이언트 — 4지국 → ChromaDB 흡수")
    ap.add_argument("--fetch", action="store_true", help="매크로 1회 끌어오기 + 박제")
    ap.add_argument("--base-url", default="http://localhost:8040", help="Stock-AI 베이스 URL")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--stats", action="store_true", help="ChromaDB 통계")
    args = ap.parse_args()

    if args.fetch:
        macro = fetch_macro(args.base_url, quiet=args.quiet)
        if macro:
            n = ingest_to_finance_brain(macro)
            if not args.quiet:
                print(f"✅ physis_finance_brain 박제: {n}건")
                # 미리보기
                data = macro.get("data", {})
                analysis = macro.get("analysis", {})
                print(f"\n📊 매크로 데이터 자산 수: {len(data) if isinstance(data, dict) else 0}")
                if isinstance(analysis, dict):
                    print(f"📈 분석 키: {list(analysis.keys())[:10]}")
                # 원본 일부 (처음 800자)
                preview = json.dumps(macro, ensure_ascii=False, indent=2)
                print(f"\n--- 미리보기 ---\n{preview[:1500]}")

    if args.stats:
        s = stats()
        print(f"📊 {s['name']}: {s['count']}개 도큐먼트")
        print(f"   메타: {s['metadata']}")
