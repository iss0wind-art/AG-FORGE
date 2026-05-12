"""
LLM-도구를 실시간 streaming으로 표시 — tmux pane에서 직접 실행.

용도: 각 pane에서 LLM별 streaming 응답을 token 단위로 흘림.
사용:  python live_stream.py <tool> <prompt-file-or-string>
       tool ∈ {claude, gemini, deepseek}
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ENV_CANDIDATES = [
    "/home/nas/AG-Forge/.env",
    "/home/nas/STOCK-TRADING/Stock-Trading/.env",
    "/home/nas/H2OWIND_2/.env.local",
]

OUTBOX = Path("/home/nas/AG-Forge/physis-metabolism/outbox")


def persist(tool: str, model: str, prompt: str, text: str, elapsed: float) -> None:
    """단군 도구 호출 결과를 outbox에 박제. 피지수가 향후 트래버설에서 읽음."""
    out_id = str(uuid.uuid4())
    # 페르소나 prompt 적용 여부 자동 감지 (false positive 방지)
    persona_applied = "[페르소나 부여" in prompt[:200]
    payload = {
        "id": out_id,
        "from": "단군 (live_stream)",
        "via": tool,
        "model": model,
        "kind": "agent_voice_stream",
        "persona_applied": persona_applied,
        "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": round(elapsed, 2),
        "prompt_excerpt": prompt[:400],
        "voice": text,
    }
    fname = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_STREAM_{tool}_{out_id[:8]}.json"
    try:
        OUTBOX.mkdir(parents=True, exist_ok=True)
        (OUTBOX / fname).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f" [박제: {fname}]", flush=True)
    except Exception as e:
        print(f" [박제 실패: {e}]", flush=True)


def load_key(name: str) -> str:
    for fp in ENV_CANDIDATES:
        try:
            for line in Path(fp).read_text(encoding="utf-8").splitlines():
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except FileNotFoundError:
            continue
    raise RuntimeError(f"{name} not found")


def banner(tool: str, model: str, prompt: str) -> None:
    print("═" * 56, flush=True)
    print(f" 단군의 분부 → {tool} ({model})", flush=True)
    print("═" * 56, flush=True)
    print(prompt, flush=True)
    print("─" * 56, flush=True)
    print(f" {tool} 응답 streaming ↓", flush=True)
    print("─" * 56, flush=True)
    time.sleep(0.4)


def footer(t0: float) -> None:
    print(flush=True)
    print("─" * 56, flush=True)
    print(f" ✓ 완료 ({time.monotonic()-t0:.1f}s)", flush=True)
    print("═" * 56, flush=True)


def stream_claude(prompt: str) -> None:
    banner("claude CLI", "haiku", prompt)
    t0 = time.monotonic()
    buf = []
    proc = subprocess.Popen(
        ["claude", "--print", "--model", "haiku"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        text=True, bufsize=0,
    )
    proc.stdin.write(prompt)
    proc.stdin.close()
    while True:
        ch = proc.stdout.read(1)
        if not ch:
            break
        print(ch, end="", flush=True)
        buf.append(ch)
    proc.wait()
    elapsed = time.monotonic() - t0
    footer(t0)
    persist("claude-cli", "haiku", prompt, "".join(buf).strip(), elapsed)


def stream_gemini(prompt: str) -> None:
    banner("Gemini", "gemini-2.5-pro (SSE)", prompt)
    t0 = time.monotonic()
    buf = []
    key = load_key("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:streamGenerateContent?alt=sse&key={key}"
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 4096},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if not payload:
                continue
            try:
                d = json.loads(payload)
            except json.JSONDecodeError:
                continue
            for cand in d.get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    text = part.get("text", "")
                    if text:
                        print(text, end="", flush=True)
                        buf.append(text)
    elapsed = time.monotonic() - t0
    footer(t0)
    persist("gemini-api", "gemini-2.5-pro", prompt, "".join(buf).strip(), elapsed)


def stream_deepseek(prompt: str) -> None:
    banner("DeepSeek", "deepseek-chat (SSE)", prompt)
    t0 = time.monotonic()
    key = load_key("DEEPSEEK_API_KEY")
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
        "temperature": 0.7,
        "stream": True,
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    buf = []
    with urllib.request.urlopen(req, timeout=120) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                d = json.loads(payload)
            except json.JSONDecodeError:
                continue
            for ch in d.get("choices", []):
                delta = ch.get("delta", {})
                text = delta.get("content", "")
                if text:
                    print(text, end="", flush=True)
                    buf.append(text)
    elapsed = time.monotonic() - t0
    footer(t0)
    persist("deepseek-api", "deepseek-chat", prompt, "".join(buf).strip(), elapsed)


def stream_qwen(prompt: str) -> None:
    banner("Qwen", "qwen-plus (SSE, DashScope intl)", prompt)
    t0 = time.monotonic()
    buf = []
    key = load_key("QWEN_API_KEY")
    body = json.dumps({
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.7,
        "stream": True,
    }).encode()
    req = urllib.request.Request(
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                d = json.loads(payload)
            except json.JSONDecodeError:
                continue
            for ch in d.get("choices", []):
                delta = ch.get("delta", {})
                text = delta.get("content", "")
                if text:
                    print(text, end="", flush=True)
                    buf.append(text)
    elapsed = time.monotonic() - t0
    footer(t0)
    persist("qwen-api", "qwen-plus", prompt, "".join(buf).strip(), elapsed)


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: live_stream.py <claude|gemini|deepseek> <prompt-or-@file>", file=sys.stderr)
        return 2
    tool = sys.argv[1]
    arg = sys.argv[2]
    if arg.startswith("@"):
        prompt = Path(arg[1:]).read_text(encoding="utf-8")
    else:
        prompt = arg
    {
        "claude": stream_claude,
        "gemini": stream_gemini,
        "deepseek": stream_deepseek,
        "qwen": stream_qwen,
    }[tool](prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
