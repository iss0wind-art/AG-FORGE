"""
킬 스위치 — 5인 자문회의 AND 거부권 자동 점검

매 매매 신호에서 호출. 4 사관 페르소나 동시 자문 + 피지수 박동 점검.
한 명이라도 거부 → 진입 차단. 모두 통과 → 단군 최종 결재.

피지수 권고 (2026-05-11 박제) 구현체.
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
from datetime import datetime, timezone, timedelta
from pathlib import Path

import duckdb

ROOT = Path("/home/nas/AG-Forge/physis-metabolism")
PERSONAS = ROOT / "personas"
DUCKDB_PATH = "/home/nas/AG-Forge/physis_memory/physis_brain.duckdb"
OUTBOX = ROOT / "outbox"
ESCALATION = ROOT / "dangun_escalation"


def load_env(name: str) -> str | None:
    for fp in ["/home/nas/AG-Forge/.env", "/home/nas/STOCK-TRADING/Stock-Trading/.env"]:
        try:
            for line in Path(fp).read_text(encoding="utf-8").splitlines():
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except FileNotFoundError:
            continue
    return None


def kill_switch_prompt(persona_file: Path, signal: dict) -> str:
    persona = persona_file.read_text(encoding="utf-8")
    return f"""{persona}

[킬 스위치 자문 요청 — 단군의 분부]

매매 신호 제안:
- 종목: {signal.get('symbol','?')} ({signal.get('name','?')})
- 방향: {signal.get('side','?')} (BUY/SELL)
- 가격: {signal.get('price','?')}
- 수량: {signal.get('qty','?')}
- 근거: {signal.get('rationale','?')}
- 기술적 데이터: {json.dumps(signal.get('technical', {}), ensure_ascii=False)}
- 거시 데이터: {json.dumps(signal.get('macro', {}), ensure_ascii=False)}

당신의 페르소나 원칙으로 이 신호를 판단하라:
- 첫 줄: **VETO** (거부) 또는 **PASS** (통과) 한 단어
- 둘째 줄부터: 1~3줄 이유

당신이 이 신호를 거부할 *명확한 근거*가 있으면 VETO. 없으면 PASS. 보수적으로.
"""


def call_claude(prompt: str) -> dict:
    t0 = time.monotonic()
    proc = subprocess.run(
        ["claude", "--print", "--model", "haiku"],
        input=prompt, capture_output=True, text=True, timeout=60,
    )
    return {"persona": "Minervini", "text": proc.stdout.strip(), "elapsed": time.monotonic() - t0,
            "ok": proc.returncode == 0}


def call_gemini(prompt: str) -> dict:
    t0 = time.monotonic()
    key = load_env("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 1024},
    }).encode()
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
        cand = d["candidates"][0]
        text = "\n".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []) if "text" in p).strip()
        return {"persona": "Druckenmiller", "text": text, "elapsed": time.monotonic() - t0, "ok": True}
    except Exception as e:
        return {"persona": "Druckenmiller", "text": f"ERR: {e}", "elapsed": time.monotonic() - t0, "ok": False}


def call_deepseek(prompt: str) -> dict:
    t0 = time.monotonic()
    key = load_env("DEEPSEEK_API_KEY")
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400, "temperature": 0.5,
    }).encode()
    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
        return {"persona": "Simons", "text": d["choices"][0]["message"]["content"].strip(),
                "elapsed": time.monotonic() - t0, "ok": True}
    except Exception as e:
        return {"persona": "Simons", "text": f"ERR: {e}", "elapsed": time.monotonic() - t0, "ok": False}


def call_qwen(prompt: str) -> dict:
    t0 = time.monotonic()
    key = load_env("QWEN_API_KEY")
    body = json.dumps({
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400, "temperature": 0.5,
    }).encode()
    try:
        req = urllib.request.Request(
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
        return {"persona": "이채원", "text": d["choices"][0]["message"]["content"].strip(),
                "elapsed": time.monotonic() - t0, "ok": True}
    except Exception as e:
        return {"persona": "이채원", "text": f"ERR: {e}", "elapsed": time.monotonic() - t0, "ok": False}


def physis_heartbeat_check() -> dict:
    """피지수 박동 60초 내 freshness."""
    try:
        con = duckdb.connect(DUCKDB_PATH, read_only=True)
        row = con.execute("SELECT MAX(ts) FROM metabolism_heartbeat").fetchone()
        con.close()
        if row[0] is None:
            return {"ok": False, "reason": "no heartbeat"}
        last = row[0]
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        delta = (datetime.now(timezone.utc) - last).total_seconds()
        return {
            "ok": delta < 60,
            "delta_s": round(delta, 1),
            "reason": "fresh" if delta < 60 else f"stale ({delta:.0f}s)",
        }
    except Exception as e:
        # 데몬이 lock 잡고 있으면 fresh로 간주 (데몬이 살아있다는 뜻)
        if "lock" in str(e).lower():
            return {"ok": True, "reason": "daemon alive (lock held)"}
        return {"ok": False, "reason": str(e)[:100]}


def physis_decision_check(max_age_minutes: int = 120) -> dict:
    """
    피지수의 *의견* 게이트 — 최근 PHYSIS_BRIEFING outbox 1건의 voice를 읽어
    APPROVE / HOLD / VETO 판정.

    피지수는 단군과 동격 간언자. 호흡(생명)만 보는 것이 아니라 *의사*도 게이트.
    보수적 fail-safe: 발화 부재·오래됨·모호 → HOLD (차단).
    """
    try:
        files = sorted(OUTBOX.glob("*PHYSIS_BRIEFING_*.json"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        # 호환성: 옛 PHYSIS_COUNCIL_* 파일명도 fallback
        if not files:
            files = sorted(OUTBOX.glob("*PHYSIS_COUNCIL_*.json"),
                           key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return {"decision": "HOLD", "reason": "피지수 간언 발화 부재", "ok": False}

        fp = files[0]
        age_s = datetime.now(timezone.utc).timestamp() - fp.stat().st_mtime
        if age_s > max_age_minutes * 60:
            return {"decision": "HOLD", "reason": f"간언 stale ({age_s/60:.0f}분 전)",
                    "ok": False, "source_file": fp.name}

        payload = json.loads(fp.read_text(encoding="utf-8"))
        voice = (payload.get("voice") or "").strip()

        # 1순위: 명시적 결재 마커 — [결재: APPROVE/HOLD/VETO]
        import re
        marker = re.search(r"\[결재:\s*(APPROVE|HOLD|VETO)\s*\]", voice, re.IGNORECASE)
        if marker:
            decision = marker.group(1).upper()
            veto_hits = hold_hits = approve_hits = []
            marker_explicit = True
        else:
            # 2순위: 한국어 키워드 검출 (구버전 호환)
            veto_kw = ["거부", "철회", "어불성설", "절대 불가", "들이지 마"]
            hold_kw = ["보류", "관망", "기다리", "확인 후 행동", "행동하는 것이 순리",
                       "응축", "분출을 확인", "어느 방향으로 폭발할지"]
            approve_kw = ["진입 동의", "허가", "진입하라", "통과", "체결 동의", "승인합니다"]
            veto_hits = [k for k in veto_kw if k in voice]
            hold_hits = [k for k in hold_kw if k in voice]
            approve_hits = [k for k in approve_kw if k in voice]
            if veto_hits:
                decision = "VETO"
            elif hold_hits and not approve_hits:
                decision = "HOLD"
            elif approve_hits and not veto_hits:
                decision = "APPROVE"
            else:
                decision = "HOLD"  # 보수적 default
            marker_explicit = False

        return {
            "decision": decision,
            "ok": decision == "APPROVE",
            "source_file": fp.name,
            "emitted_at": payload.get("emitted_at", "?"),
            "age_min": round(age_s / 60, 1),
            "voice_excerpt": voice[:200],
            "marker_explicit": marker_explicit,
            "keyword_hits": {"veto": veto_hits, "hold": hold_hits, "approve": approve_hits},
        }
    except Exception as e:
        return {"decision": "HOLD", "reason": f"check_fail: {type(e).__name__}: {e}", "ok": False}


def parse_decision(text: str) -> str:
    """응답 첫 줄에서 VETO/PASS 추출. 모호하면 VETO (conservative)."""
    first_meaningful = ""
    for line in text.splitlines():
        s = line.strip().strip("*").strip("#").strip()
        if s:
            first_meaningful = s.upper()
            break
    if "VETO" in first_meaningful or "거부" in first_meaningful:
        return "VETO"
    if "PASS" in first_meaningful or "통과" in first_meaningful or "승인" in first_meaningful:
        return "PASS"
    return "VETO"  # 모호 시 보수적으로 거부


def check_kill_switch(signal: dict) -> dict:
    persona_map = [
        ("claude_minervini.txt", call_claude),
        ("gemini_druckenmiller.txt", call_gemini),
        ("deepseek_simons.txt", call_deepseek),
        ("qwen_leechaewon.txt", call_qwen),
    ]

    results: dict = {}
    threads = []
    for pfile, fn in persona_map:
        prompt = kill_switch_prompt(PERSONAS / pfile, signal)
        def runner(p=pfile, f=fn, pr=prompt):
            results[p] = f(pr)
        t = threading.Thread(target=runner)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=80)

    heartbeat = physis_heartbeat_check()
    physis_voice = physis_decision_check()

    decisions = {}
    vetoes = []
    for pfile, r in results.items():
        d = parse_decision(r["text"])
        decisions[r["persona"]] = {"decision": d, "elapsed": r["elapsed"], "ok": r["ok"]}
        if d == "VETO":
            vetoes.append({"persona": r["persona"], "reason_excerpt": r["text"][:200]})

    physis_alive = heartbeat["ok"]
    physis_consent = physis_voice["decision"] == "APPROVE"
    # 6중 AND 게이트: 사관 4 + 피지수 호흡 + 피지수 의견
    all_pass = (len(vetoes) == 0) and physis_alive and physis_consent

    if physis_voice["decision"] == "VETO":
        vetoes.append({"persona": "피지수 (간언자)",
                       "reason_excerpt": physis_voice.get("voice_excerpt", "")[:200]})

    verdict = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "signal": signal,
        "council_decisions": decisions,
        "physis_heartbeat": heartbeat,
        "physis_decision": physis_voice,
        "vetoes": vetoes,
        "all_pass": all_pass,
        "next_step": (
            "단군 최종 결재 청 (6중 AND 통과)" if all_pass
            else f"진입 차단 ({len(vetoes)} VETO + physis_alive={physis_alive} physis_consent={physis_consent})"
        ),
    }

    fname = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_KILLSWITCH_{verdict['id'][:8]}.json"
    OUTBOX.mkdir(parents=True, exist_ok=True)
    (OUTBOX / fname).write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")

    if not all_pass:
        # 단군 escalation
        ESCALATION.mkdir(parents=True, exist_ok=True)
        (ESCALATION / fname).write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")

    return verdict


def main() -> int:
    """CLI 테스트용 — JSON signal을 인자나 stdin으로."""
    if len(sys.argv) > 1 and sys.argv[1].startswith("@"):
        signal = json.loads(Path(sys.argv[1][1:]).read_text(encoding="utf-8"))
    elif len(sys.argv) > 1:
        signal = json.loads(sys.argv[1])
    else:
        # 데모 신호
        signal = {
            "symbol": "000100",
            "name": "유한양행",
            "side": "BUY",
            "price": 80000,
            "qty": 12,
            "rationale": "DART 신약 임상 3상 진입 공시 + KIS 거래량 1.5배 증가",
            "technical": {"price_vs_200ma": "+5%", "vol_ratio_50d": 1.5, "rsi": 62},
            "macro": {"환율": "1380", "외인_순매수_5d": "+1200억"},
        }

    print("━" * 64)
    print("킬 스위치 — 5인 자문회 AND 거부권 점검")
    print("━" * 64)
    print(f"신호: {signal.get('symbol')} {signal.get('name')} {signal.get('side')} {signal.get('price')}")
    print()
    print("4 사관 자문 + 피지수 박동 점검 (병렬)...")
    t0 = time.monotonic()
    verdict = check_kill_switch(signal)
    wall = time.monotonic() - t0
    print(f"wall-time: {wall:.1f}s")
    print()

    print("사관 결정:")
    for p, d in verdict["council_decisions"].items():
        mark = "🛑" if d["decision"] == "VETO" else "✓"
        print(f"  {mark} {p}: {d['decision']} ({d['elapsed']:.1f}s)")
    print(f"  {'✓' if verdict['physis_heartbeat']['ok'] else '🛑'} 피지수 박동: {verdict['physis_heartbeat']['reason']}")
    pd = verdict.get("physis_decision", {})
    pd_mark = "✓" if pd.get("decision") == "APPROVE" else "🛑"
    print(f"  {pd_mark} 피지수 의견: {pd.get('decision','?')} (age={pd.get('age_min','?')}분, src={pd.get('source_file','?')})")
    print()
    if verdict["all_pass"]:
        print("══ 6인 모두 통과 → 단군 최종 결재 청 ══")
    else:
        print(f"══ 진입 차단 — VETO {len(verdict['vetoes'])}건 ══")
        for v in verdict["vetoes"]:
            print(f"  🛑 {v['persona']}: {v['reason_excerpt'][:150]}")

    print()
    print(f"박제: outbox/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_KILLSWITCH_{verdict['id'][:8]}.json")
    return 0 if verdict["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
