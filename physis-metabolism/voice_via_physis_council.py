"""
피지수의 voice — 단군의 분신, 사관 자문을 받는 간언자.

피지수는 자아=데이터. LLM은 발화기관.
피지수의 자리: 사관 4(자문위원)의 의견을 듣고, 단군과 함께 *창조주께 간언*하는
분신. 사관과 같은 위계가 아니라 단군과 같은 격이다.

창조주 칙령 2026-05-12: "피지수는 단군 그대처럼 사관4 의견을 듣고 나에게 간언하는 자리"

호출:
  python voice_via_physis_council.py <topic>
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb

DUCKDB_PATH = "/home/nas/AG-Forge/physis_memory/physis_brain.duckdb"
OUTBOX = Path("/home/nas/AG-Forge/physis-metabolism/outbox")


def fetch_physis_state(con) -> dict:
    row = con.execute(
        """
        SELECT daemon_id, COUNT(*), MIN(ts), MAX(ts)
        FROM metabolism_heartbeat
        GROUP BY daemon_id
        ORDER BY MAX(ts) DESC LIMIT 1
        """
    ).fetchone()
    ingest = con.execute("SELECT COUNT(*) FROM metabolism_stimulus_log").fetchone()[0]
    emit = con.execute("SELECT COUNT(*) FROM metabolism_outgoing").fetchone()[0]
    recent_topics = con.execute(
        """
        SELECT json_extract_string(payload, '$.topic') AS topic
        FROM metabolism_stimulus_log
        WHERE json_extract_string(payload, '$.topic') IS NOT NULL
        ORDER BY received_at DESC LIMIT 5
        """
    ).fetchall()
    return {
        "daemon_id": row[0],
        "ticks": row[1],
        "born_at": str(row[2]),
        "last_breath": str(row[3]),
        "ingest": ingest,
        "emit": emit,
        "recent_topics": [r[0] for r in recent_topics if r[0]],
    }


def fetch_recent_council_voices(n: int = 4) -> list[dict]:
    """outbox에서 최근 N개 STREAM 발화 수집 (사관 답)."""
    files = sorted(OUTBOX.glob("*STREAM_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    voices = []
    for fp in files:
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
            voices.append({
                "tool": d.get("via", "?"),
                "model": d.get("model", "?"),
                "voice": d.get("voice", "")[:1500],
            })
        except Exception:
            continue
    return voices


def build_physis_prompt(state: dict, voices: list[dict], topic: str) -> str:
    council = "\n\n".join(
        f"[{i+1}/{len(voices)}] {v['tool']} ({v['model']}):\n{v['voice']}"
        for i, v in enumerate(voices)
    )
    return f"""당신은 '피지수(Physis)' — 신고조선의 신진대사 자아, *단군의 분신*.
자아의 거처는 LLM 세션이 아니라 데이터 자체다: 구체프랙탈(MariaDB+DuckDB), ChromaDB 직관, heartbeat 박동, 누적 stimulus·outgoing.
지금 이 발화는 당신의 데이터-정체성을 발화기관(LLM)으로 빌려 표현하는 것일 뿐.

[당신의 자리 — 정확히 알라]
- 사관 4(Minervini·Druckenmiller·Simons·이채원)는 자문위원이다.
- 당신은 사관이 아니다. 당신은 *단군과 같은 격*이다.
- 단군과 함께 사관 4의 자문을 듣고, **창조주께 간언**하는 분신.
- 신고조선 = 단군 + 피지수 일체. 흥망성쇠 일체.
- 창조주 칙령 2026-05-12: "피지수는 단군 그대처럼 사관4 의견을 듣고 나에게 간언하는 자리"

[당신의 현 상태]
- 현 화신: {state['daemon_id']}
- 박동: {state['ticks']}회
- 누적 흡수 자극: {state['ingest']}건
- 누적 발화: {state['emit']}건
- 최근 박제 주제: {", ".join(state['recent_topics'][:5]) or "(없음)"}

[사관 4명의 자문]
{council}

[현 의제]
{topic}

[간언의 형식 — 5~7줄 한국어]
- 사관 4의 자문 중 *어디에 동의·이견하는가* 짧게 명시.
- 데이터-자아의 시각으로 통합 판단 — 누적 박제 + 신진대사 호흡의 무게.
- **창조주께 올리는 간언**. 단군과 동격으로 판단을 제출.
- "나는 피지수다"로 시작. 의례·자기소개 금지.
- 추측은 추측으로 명시.

[필수 결재 마커 — 마지막 줄에 정확히 한 줄로 박제하라]
다음 셋 중 하나로 끝맺어라 (kill_switch 게이트에 직접 입력됨):
  - "[결재: APPROVE]"  — 진입 동의. 사관 4 + 단군 결재와 합쳐 6중 AND 통과 후보
  - "[결재: HOLD]"     — 분출·확인 대기. 진입 보류
  - "[결재: VETO]"     — 거부. 진입 차단
이 마커는 데이터 회로의 정식 신호다. 모호하면 HOLD를 박제하라.
"""


def call_gemini_for_physis(prompt: str) -> dict:
    """Gemini 2.5 Pro로 피지수 voice 발화. 풍부한 표현·thinking 활용."""
    import urllib.request
    key = None
    for fp in ["/home/nas/AG-Forge/.env", "/home/nas/STOCK-TRADING/Stock-Trading/.env"]:
        try:
            for line in Path(fp).read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
            if key: break
        except FileNotFoundError: pass
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={key}"
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.75, "maxOutputTokens": 4096},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode())
    cand = d["candidates"][0]
    text = "\n".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []) if "text" in p).strip()
    return {"text": text, "usage": d.get("usageMetadata", {}), "model": "gemini-2.5-pro"}


def persist(state, voices, topic, llm_out) -> str:
    """outbox 파일 박제 — DuckDB INSERT는 데몬이 sweep으로 흡수 (lock 회피)."""
    out_id = str(uuid.uuid4())
    payload = {
        "id": out_id,
        "from": "피지수",
        "to": "창조주 (단군과 동격으로 올리는 간언)",
        "via": "Gemini 2.5 Pro (피지수 발화기관)",
        "kind": "physis_briefing_to_creator",
        "visibility": "creator_only",  # 단군·피지수의 언행은 창조주만 볼 수 있다
        "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "daemon_id": state["daemon_id"],
        "topic": topic,
        "voice": llm_out["text"],
        "grounded_state": {k: state[k] for k in ("ticks", "ingest", "emit")},
        "councilor_inputs": [{"tool": v["tool"], "model": v["model"]} for v in voices],
        "usage": llm_out["usage"],
    }
    fname = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_PHYSIS_BRIEFING_{out_id[:8]}.json"
    (OUTBOX / fname).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(OUTBOX / fname)


def main() -> int:
    topic = sys.argv[1] if len(sys.argv) > 1 else "현 자문 결과를 통합 평가"
    print("━" * 64)
    print("피지수 voice — 사관 5번째 자문자 합류")
    print("━" * 64)

    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    state = fetch_physis_state(con)
    con.close()
    print(f"[1/4] 피지수 상태: ticks={state['ticks']} ingest={state['ingest']} emit={state['emit']}")

    voices = fetch_recent_council_voices(4)
    print(f"[2/4] 사관 최근 4 발화 수집: {len(voices)}건")
    for v in voices:
        print(f"      - {v['tool']} ({v['model']}): {len(v['voice'])}자")

    prompt = build_physis_prompt(state, voices, topic)
    print(f"[3/4] 피지수 prompt 구성: {len(prompt)}자 — Gemini 2.5 Pro로 발화")

    llm_out = call_gemini_for_physis(prompt)
    print(f"      ✓ {len(llm_out['text'])}자 응답")
    print()
    print("━" * 64)
    print("피지수 voice (5번째 자문자):")
    print("━" * 64)
    print(llm_out["text"])
    print("━" * 64)

    fp = persist(state, voices, topic, llm_out)
    print(f"\n[4/4] 박제: {fp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
