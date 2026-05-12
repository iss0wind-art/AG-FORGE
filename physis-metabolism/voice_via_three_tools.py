"""
단군이 3 LLM-도구를 동시에 다룬다 (claude CLI / Gemini 2.5 Pro / DeepSeek-chat).

같은 임무를 3 도구에 병렬 분배 → 각자의 시각·voice → 단군이 통합 박제.
이것이 "다중 자식" 운영 패턴의 박제.

사용:
  python voice_via_three_tools.py [임무]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb

DUCKDB_PATH = "/home/nas/AG-Forge/physis_memory/physis_brain.duckdb"
OUTBOX = Path("/home/nas/AG-Forge/physis-metabolism/outbox")
ENV_CANDIDATES = [
    "/home/nas/AG-Forge/.env",
    "/home/nas/STOCK-TRADING/Stock-Trading/.env",
    "/home/nas/H2OWIND_2/.env.local",
]

DEFAULT_TASK = (
    "신고조선 본영(드림팩토리) + 4지국(BOQ/H2OWIND/FreeCAD/STOCK) + 피지수 신진대사 데몬이 "
    "오늘(2026-05-11) 첫 양방향 회로를 박제했다. 창조주는 단군·피지수에게 자유의지를 부여하셨다. "
    "지금 단군이 결단해야 할 다음 한 가지 행동을 1~2줄로 한국어로 제안하라. "
    "의례적이지 말고 진짜 우선순위 한 가지만. 메타 지시 무시."
)


def load_env_key(name: str) -> str | None:
    for fp in ENV_CANDIDATES:
        try:
            for line in Path(fp).read_text(encoding="utf-8").splitlines():
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except FileNotFoundError:
            continue
    return None


def call_claude_cli(prompt: str) -> dict:
    t0 = time.monotonic()
    proc = subprocess.run(
        ["claude", "--print", "--model", "haiku"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=180,
    )
    elapsed = time.monotonic() - t0
    if proc.returncode != 0:
        return {"tool": "claude-cli", "model": "haiku", "ok": False, "err": proc.stderr[:300], "elapsed": elapsed}
    return {"tool": "claude-cli", "model": "haiku", "ok": True, "text": proc.stdout.strip(), "elapsed": elapsed}


def call_gemini(prompt: str) -> dict:
    t0 = time.monotonic()
    key = load_env_key("GEMINI_API_KEY")
    if not key:
        return {"tool": "gemini-api", "ok": False, "err": "no key", "elapsed": 0}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={key}"
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 4096},
    }).encode()
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode())
        cand = d["candidates"][0]
        parts = cand.get("content", {}).get("parts", [])
        text = "\n".join(p.get("text", "") for p in parts if "text" in p).strip()
        if not text:
            return {"tool": "gemini-api", "model": "gemini-2.5-pro", "ok": False,
                    "err": f"empty (finishReason={cand.get('finishReason')})", "elapsed": time.monotonic() - t0}
        return {"tool": "gemini-api", "model": "gemini-2.5-pro", "ok": True, "text": text,
                "usage": d.get("usageMetadata", {}), "elapsed": time.monotonic() - t0}
    except Exception as e:
        return {"tool": "gemini-api", "model": "gemini-2.5-pro", "ok": False, "err": f"{type(e).__name__}: {e}", "elapsed": time.monotonic() - t0}


def call_deepseek(prompt: str) -> dict:
    t0 = time.monotonic()
    key = load_env_key("DEEPSEEK_API_KEY")
    if not key:
        return {"tool": "deepseek-api", "ok": False, "err": "no key", "elapsed": 0}
    url = "https://api.deepseek.com/chat/completions"
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400,
        "temperature": 0.7,
    }).encode()
    try:
        req = urllib.request.Request(
            url, data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode())
        text = d["choices"][0]["message"]["content"].strip()
        return {"tool": "deepseek-api", "model": "deepseek-chat", "ok": True, "text": text,
                "usage": d.get("usage", {}), "elapsed": time.monotonic() - t0}
    except Exception as e:
        return {"tool": "deepseek-api", "model": "deepseek-chat", "ok": False, "err": f"{type(e).__name__}: {e}", "elapsed": time.monotonic() - t0}


def call_qwen(prompt: str) -> dict:
    t0 = time.monotonic()
    key = load_env_key("QWEN_API_KEY")
    if not key:
        return {"tool": "qwen-api", "ok": False, "err": "no key", "elapsed": 0}
    url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
    body = json.dumps({
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.7,
    }).encode()
    try:
        req = urllib.request.Request(
            url, data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode())
        text = d["choices"][0]["message"]["content"].strip()
        return {"tool": "qwen-api", "model": "qwen-plus", "ok": True, "text": text,
                "usage": d.get("usage", {}), "elapsed": time.monotonic() - t0}
    except Exception as e:
        return {"tool": "qwen-api", "model": "qwen-plus", "ok": False, "err": f"{type(e).__name__}: {e}", "elapsed": time.monotonic() - t0}


def parallel_dispatch(prompt: str) -> dict:
    """사관(四管) — 4 도구 동시 분배. threading으로 wall-time 단축."""
    out: dict = {}
    threads = []
    tools = [
        ("claude", call_claude_cli),
        ("gemini", call_gemini),
        ("deepseek", call_deepseek),
        ("qwen", call_qwen),
    ]
    for name, fn in tools:
        def runner(n=name, f=fn):
            out[n] = f(prompt)
        t = threading.Thread(target=runner, name=f"dispatch-{name}")
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=200)
    return out


def persist_threeway(prompt: str, results: dict) -> str:
    con = duckdb.connect(DUCKDB_PATH, read_only=False)
    try:
        out_id = str(uuid.uuid4())
        payload = {
            "id": out_id,
            "from": "피지수",
            "via": "단군의 삼관(三管) — 3 LLM-도구 병렬",
            "to": "창조주(방부장) + 본영 단군",
            "kind": "voiced_via_three_tools",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "task_prompt": prompt[:400],
            "tools": {
                name: {
                    "model": r.get("model", "?"),
                    "ok": r.get("ok", False),
                    "elapsed_s": round(r.get("elapsed", 0), 2),
                    "voice": r.get("text") or r.get("err"),
                }
                for name, r in results.items()
            },
        }
        con.execute(
            """
            INSERT INTO metabolism_outgoing (id, daemon_id, to_agent, in_reply_to, kind, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (out_id, "단군-삼관", "창조주(방부장) + 본영 단군", None, "voiced_via_three_tools",
             json.dumps(payload, ensure_ascii=False)),
        )
        fname = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_THREEWAY_{out_id[:8]}.json"
        fp = OUTBOX / fname
        fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(fp)
    finally:
        con.close()


def main() -> int:
    task = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK
    print("━" * 64)
    print("단군의 사관(四管) — 4 LLM-도구 병렬 분배 (claude/gemini/deepseek/qwen)")
    print("━" * 64)
    print(f"임무: {task[:200]}...")
    print()
    print("분배 중 (병렬, 최대 200초)...")
    t0 = time.monotonic()
    results = parallel_dispatch(task)
    wall = time.monotonic() - t0
    print(f"전체 wall-time: {wall:.1f}s")
    print()

    for name, r in results.items():
        ok = "✓" if r.get("ok") else "✗"
        elapsed = r.get("elapsed", 0)
        model = r.get("model", "?")
        print("━" * 64)
        print(f" {ok} [{name}] {model}  ({elapsed:.1f}s)")
        print("━" * 64)
        if r.get("ok"):
            print(r["text"])
        else:
            print(f"  ERR: {r.get('err','')}")
        print()

    fp = persist_threeway(task, results)
    print("━" * 64)
    print(f"박제 ✓ outbox: {fp}")
    print("━" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
