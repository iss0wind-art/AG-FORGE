"""
시장 개장 전 사전 브리핑 — 08:30 KST 자동 자문.

사관 4명에게 각자 데이터 슬라이스 시각으로 "오늘 첫 1시간 핵심 점검"을 자문.
피지수에 stimulus로 박제 + outbox.

cron 등록 권고:
  30 8 * * 1-5  /home/nas/AG-Forge/.venv/bin/python /home/nas/AG-Forge/physis-metabolism/preopen_brief.py

또는 단군이 매일 직접 실행. PM2에 cron_restart로도 가능.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/nas/AG-Forge/physis-metabolism")
PERSONAS = ROOT / "personas"
STIMULI = ROOT / "stimuli"
LIVE_STREAM = ROOT / "live_stream.py"
PY = "/home/nas/AG-Forge/.venv/bin/python"

# 각 페르소나에게 자기 데이터 슬라이스에 맞춘 사전 질문
SLICED_QUESTIONS = {
    "claude": (
        "오늘(2026-05-12) 한국 시장 개장 30분간 당신(미너비니)의 차트·기술 시각으로 "
        "가장 먼저 점검할 단 한 가지: 신고가 근접 + 거래량 폭증을 동시에 만족하는 종목군이 "
        "어떤 패턴(VCP·flat base 등)을 보이고 있을 가능성이 높은가? "
        "2~3줄로 답하라. 데이터 없으면 일반론. \"나는 미너비니다\"로 시작."
    ),
    "gemini": (
        "오늘 한국 시장 개장 30분간 당신(드러켄밀러)의 거시·환율 시각으로 "
        "원/달러·KOSPI 선물·미국 전일 마감을 결합해 보면, "
        "외인 순매수 방향과 강도에 대해 어떤 가설이 가장 합리적인가? "
        "2~3줄. 가설은 가설로 명시. \"나는 드러켄밀러다\"로 시작."
    ),
    "deepseek": (
        "오늘 한국 시장 개장 30분간 당신(사이먼스)의 정량 시각으로 "
        "KOSPI200/KOSDAQ150 선물 1분봉 상관계수가 0.3 이하로 떨어진다면 "
        "그 패턴이 무엇을 의미하며 어떤 통계적 거래가 가능한가? "
        "2~3줄. 정량 임계값 포함. \"나는 사이먼스다\"로 시작."
    ),
    "qwen": (
        "오늘 한국 시장 개장 30분간 당신(이채원)의 공시·거버넌스 시각으로 "
        "오늘 공시·뉴스에서 가장 경계해야 할 신호 유형 한 가지는? "
        "(예: 자기주식 매입 철회, 지배구조 변경, 공매도 급증) "
        "2~3줄. \"나는 이채원이다\"로 시작."
    ),
}


def compose_prompt(tool: str) -> Path:
    persona_file_map = {
        "claude": "claude_minervini.txt",
        "gemini": "gemini_druckenmiller.txt",
        "deepseek": "deepseek_simons.txt",
        "qwen": "qwen_leechaewon.txt",
    }
    persona = (PERSONAS / persona_file_map[tool]).read_text(encoding="utf-8")
    q = SLICED_QUESTIONS[tool]
    full = persona + "\n\n[학습 — 사전 브리핑]\n" + q + "\n"
    fp = Path(f"/tmp/preopen_{tool}.txt")
    fp.write_text(full, encoding="utf-8")
    return fp


def call_one(tool: str, prompt_file: Path) -> dict:
    t0 = time.monotonic()
    proc = subprocess.run(
        [PY, str(LIVE_STREAM), tool, f"@{prompt_file}"],
        capture_output=True, text=True, timeout=120,
    )
    return {
        "tool": tool,
        "elapsed": time.monotonic() - t0,
        "stdout_tail": proc.stdout[-800:] if proc.stdout else "",
        "ok": proc.returncode == 0,
    }


def main() -> int:
    print("━" * 64)
    print(f"사전 브리핑 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("━" * 64)
    # 페르소나 prompt 박제
    prompts = {tool: compose_prompt(tool) for tool in SLICED_QUESTIONS}
    # 4 사관 병렬 (각자 자기 슬라이스 질문)
    results: dict = {}
    threads = []
    for tool, pf in prompts.items():
        t = threading.Thread(target=lambda x=tool, p=pf: results.update({x: call_one(x, p)}))
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=180)

    summary = {
        "kind": "preopen_brief",
        "source": "단군 (preopen_brief.py)",
        "to": "피지수",
        "topic": "시장 개장 30분 사전 브리핑 — 사관 4 슬라이스 자문",
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "results": {k: {"elapsed": v["elapsed"], "ok": v["ok"]} for k, v in results.items()},
    }
    # 피지수 stimulus로 떨굼
    sfp = STIMULI / f"preopen_brief_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    sfp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n사전 브리핑 박제 (피지수 흡수 예정): {sfp.name}")
    print(f"개별 응답은 live_stream.py가 outbox/STREAM_*.json로 자동 박제.")
    for tool, r in results.items():
        print(f"  - {tool}: {'✓' if r['ok'] else '✗'} ({r['elapsed']:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
