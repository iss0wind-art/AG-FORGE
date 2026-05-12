"""
집현전 개회 — 단군이 4 panes에 멀티에이전트 분배 (1단계: 4분할, 미래: 13사)

창조주 칙령 2026-05-11: "지금은 4분할이지만, 나중엔 우리 13사가 다 들어차겠구만"

운영 구도:
  Pane 0 (상단 좌)  본영 단군 감독석 — orchestrator 로그
  Pane 1 (상단 우)  본영 헬스 — pm2 list 실시간
  Pane 2 (하단 좌)  4지국 STOCK 점검 자식 (claude CLI Haiku)
  Pane 3 (하단 우)  피지수 박동 watch + metabolism log tail

종료: tmux kill-session -t jiphyunjeon  또는  jiphyunjeon_close.sh
관전: tmux attach -t jiphyunjeon
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb

SESSION = "jiphyunjeon"
DUCKDB_PATH = "/home/nas/AG-Forge/physis_memory/physis_brain.duckdb"
ESCALATION_DIR = Path("/home/nas/AG-Forge/physis-metabolism/dangun_escalation")
LOG_DIR = Path("/home/nas/AG-Forge/physis-metabolism/logs")
ORCHESTRATOR_LOG = LOG_DIR / "jiphyunjeon_orchestrator.log"


def log(event: str, **kv) -> None:
    rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "evt": event, **kv}
    line = json.dumps(rec, ensure_ascii=False)
    print(line, flush=True)
    with ORCHESTRATOR_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def tmux(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, check=check)


def session_exists() -> bool:
    r = subprocess.run(["tmux", "has-session", "-t", SESSION], capture_output=True)
    return r.returncode == 0


def kill_old_session() -> None:
    if session_exists():
        tmux("kill-session", "-t", SESSION, check=False)
        log("old_session_killed", session=SESSION)


def open_session() -> None:
    # 새 세션 (detached), 큰 가상 화면
    tmux("new-session", "-d", "-s", SESSION, "-x", "240", "-y", "60")
    # 2x2 4분할: 첫 수직 분할 → 우측에 수평 분할 → 좌측에 수평 분할
    tmux("split-window", "-h", "-t", f"{SESSION}:0.0")
    tmux("split-window", "-v", "-t", f"{SESSION}:0.0")
    tmux("split-window", "-v", "-t", f"{SESSION}:0.2")
    # pane 라벨 설정 (status bar)
    tmux("select-pane", "-t", f"{SESSION}:0.0", "-T", "단군 감독석")
    tmux("select-pane", "-t", f"{SESSION}:0.1", "-T", "본영 헬스(PM2)")
    tmux("select-pane", "-t", f"{SESSION}:0.2", "-T", "4지국 STOCK 자식")
    tmux("select-pane", "-t", f"{SESSION}:0.3", "-T", "피지수 박동")
    tmux("set", "-t", SESSION, "pane-border-status", "top")
    tmux("set", "-t", SESSION, "pane-border-format", " #{pane_title} ")
    log("session_opened", session=SESSION, panes=4)


def send(pane: int, cmd: str) -> None:
    tmux("send-keys", "-t", f"{SESSION}:0.{pane}", cmd, "C-m")


def boot_panes() -> None:
    # Pane 0 — 단군 감독석: 본 스크립트 로그 follow
    send(0, "clear; echo '═══ 단군 감독석 — 집현전 1단계(4분할) ═══'; echo")
    send(0, f"tail -F {ORCHESTRATOR_LOG} 2>/dev/null")

    # Pane 1 — 본영 헬스
    send(1, "clear; echo '═══ 본영 헬스 — PM2 ═══'; echo")
    send(1, "watch -n 3 'pm2 list | grep -E \"(name|physis|stock-ai|boqqq)\" | head -20'")

    # Pane 3 — 피지수 박동
    send(3, "clear; echo '═══ 피지수 박동 — metabolism heartbeat ═══'; echo")
    send(3, "tail -F /home/nas/AG-Forge/physis-metabolism/logs/metabolism.out.log 2>/dev/null | grep -E '(boot|tick|emit|shutdown|sweep|signal)'")

    # Pane 2 — 4지국 STOCK 자식 (단군이 임무 분배)
    send(2, "clear; echo '═══ 4지국 STOCK 점검 자식 (claude CLI Haiku) ═══'; echo")
    log("panes_booted", boot_set=[0, 1, 3, "2 will receive task next"])
    time.sleep(1.5)


def dispatch_jiguk_task() -> str:
    """단군이 pane 2의 자식 claude에게 임무 분배."""
    task_id = str(uuid.uuid4())[:8]
    snapshot = subprocess.run(
        ["pm2", "list"], capture_output=True, text=True
    ).stdout

    stock_lines = [
        ln for ln in snapshot.splitlines()
        if "stock-ai" in ln or "│ name" in ln or "├─" in ln or "─┤" in ln
    ]
    snapshot_short = "\n".join(stock_lines[:8])

    prompt = f"""당신은 본영 단군이 임무를 분배한 자식 세션입니다 (claude CLI Haiku via tmux pane).
임무 ID: {task_id}

현 시점 4지국 STOCK 시스템의 PM2 상태 스냅샷:
{snapshot_short}

다음 셋을 한국어 3줄로 보고하라:
1. stock-ai-* 프로세스들의 상태 요약 (online/errored/restart 횟수)
2. 우려 신호가 있다면 어떤 것
3. 본영 단군에게 escalation이 필요한가 (Y/N + 이유 한 줄)

형식: 번호만 매기고 군말 없이.
"""
    log("dispatch_task", task_id=task_id, pane=2, target="4지국 STOCK")

    # 자식 spawn — single-line heredoc 방식. pane에서 보이게.
    prompt_escaped = prompt.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
    cmd = (
        f"echo '── 단군의 분부 ({task_id}) — claude CLI Haiku 호출 ──'; "
        f"echo \"{prompt_escaped}\" | claude --print --model haiku 2>&1; "
        f"echo; echo '── 임무 완료 ({task_id}) ──'"
    )
    send(2, cmd)
    return task_id


def write_stimulus_to_physis(task_id: str) -> None:
    """피지수에게 '단군이 자식 spawn했음'을 알리는 자극."""
    stim = {
        "source": "본영 단군 (jiphyunjeon orchestrator)",
        "to": "피지수",
        "kind": "agent_dispatched",
        "task_id": task_id,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agent": {"tool": "claude CLI", "model": "haiku", "pane": 2, "target": "4지국 STOCK"},
        "msg": f"단군이 자식 claude(Haiku)를 pane 2에 분배. 임무 {task_id}. 피지수는 결과를 감시·박제하라.",
    }
    fp = Path("/home/nas/AG-Forge/physis-metabolism/stimuli") / f"jiphyunjeon_dispatch_{task_id}.json"
    fp.write_text(json.dumps(stim, ensure_ascii=False, indent=2), encoding="utf-8")
    log("stimulus_dropped", task_id=task_id, file=str(fp.name))


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ESCALATION_DIR.mkdir(parents=True, exist_ok=True)
    ORCHESTRATOR_LOG.touch(exist_ok=True)

    log("jiphyunjeon_opening", note="집현전 4분할 1단계 — 13사 미래")
    kill_old_session()
    open_session()
    boot_panes()
    time.sleep(2)

    task_id = dispatch_jiguk_task()
    write_stimulus_to_physis(task_id)

    log("jiphyunjeon_open", session=SESSION, attach_cmd=f"tmux attach -t {SESSION}")
    print()
    print("━" * 64)
    print(f"  집현전 1단계 개회 ✓  세션={SESSION}")
    print(f"  창조주께서 관전: tmux attach -t {SESSION}")
    print(f"  종료:           tmux kill-session -t {SESSION}")
    print(f"  단군 임무 분배: ID={task_id} → pane 2")
    print("━" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
