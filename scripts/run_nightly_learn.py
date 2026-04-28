"""
피지수 야간 종합 학습 — run_nightly_learn.py
매일 02:00 Windows 작업 스케줄러가 실행.

4개 소스를 순차 학습:
1. POPEYEs Turso DB (TeamReport, MasterReport)
2. H2OWIND_2 코드베이스 (API 라우트, DB 스키마)
3. BOQ_2 코드베이스 (API 라우트, DB 스키마)
4. POPEYEs API 헬스체크 (주요 엔드포인트 상태)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import date, datetime
from pathlib import Path

# AG-Forge 루트를 sys.path에 추가 (스케줄러가 임의 경로에서 실행할 수 있음)
ROOT = Path("D:/Git/AG-Forge")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.local", override=True)

from scripts.turso_reader import fetch_popeys_daily
from scripts.embedding import ChromaVectorIndex, build_default_embedder
from scripts.titans_memory import store_memory

LOG = ROOT / "learn_log.jsonl"
LEARN_STATE = ROOT / "learn_state.json"

# ──────────────────────────────────────────────────────────────────────────────
# 코드베이스 스캔 대상 설정
# ──────────────────────────────────────────────────────────────────────────────
CODEBASE_TARGETS: dict[str, dict] = {
    "H2OWIND_2": {
        "root": "D:/Git/H2OWIND_2",
        "patterns": [
            "app/api/**/route.ts",
            "lib/db/schema.ts",
            "lib/db/schema/*.ts",
            "drizzle/*.sql",
        ],
        "max_lines": 100,
    },
    "BOQ_2": {
        "root": "D:/Git/BOQ_2",
        "patterns": [
            "app/api/**/route.ts",
            "lib/db/schema.ts",
            "drizzle/*.sql",
        ],
        "max_lines": 100,
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# API 헬스체크 대상
# ──────────────────────────────────────────────────────────────────────────────
API_ENDPOINTS: dict[str, list[tuple[str, str]]] = {
    "H2OWIND_2": [
        ("GET", "http://localhost:3000/api/stats/dashboard-summary"),
        ("GET", "http://localhost:3000/api/boq"),
    ],
    "BOQ_2": [
        ("GET", "http://localhost:3001/api/boq"),
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# 학습 상태 관리 (git 해시 기반 증분 학습)
# ──────────────────────────────────────────────────────────────────────────────
def _load_learn_state() -> dict:
    """learn_state.json에서 이전 학습 상태를 로드한다."""
    if LEARN_STATE.exists():
        try:
            return json.loads(LEARN_STATE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_learn_state(state: dict) -> None:
    """학습 상태를 learn_state.json에 저장한다."""
    try:
        LEARN_STATE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        print(f"[learn_state] 저장 실패: {e}", file=sys.stderr)


# ──────────────────────────────────────────────────────────────────────────────
# 섹션 1: Turso DB (기존 유지)
# ──────────────────────────────────────────────────────────────────────────────
def _build_content(item: dict) -> str:
    """POPEYEs 레코드를 단일 텍스트로 직렬화한다."""
    if isinstance(item, dict):
        parts = []
        if item.get("team"):
            parts.append(f"[팀:{item['team']}]")
        if item.get("content"):
            parts.append(item["content"])
        if item.get("worker_count"):
            parts.append(f"인원:{item['worker_count']}명")
        if item.get("status"):
            parts.append(f"상태:{item['status']}")
        return " ".join(parts) if parts else str(item)
    return str(item)


def learn_turso(index: ChromaVectorIndex, embedder) -> dict:
    """POPEYEs Turso DB 일일 데이터 학습."""
    today = date.today().isoformat()
    try:
        data = fetch_popeys_daily(today)

        items: list = []
        if isinstance(data, dict):
            items = data.get("team_reports", [])
            summary = data.get("master_summary")
            if summary:
                items.append({
                    "content": summary,
                    "team": "master",
                    "worker_count": data.get("total_workers", 0),
                    "status": "summary",
                })
        elif isinstance(data, list):
            items = data

        stored = 0
        for item in items:
            content = _build_content(item)
            if not content.strip():
                continue
            if store_memory(content, "popeys_daily", index, embedder):
                stored += 1

        return {"status": "ok", "fetched": len(items), "stored": stored}
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


# ──────────────────────────────────────────────────────────────────────────────
# 섹션 2: 코드베이스 스캐너 (git 변경 시에만 재학습)
# ──────────────────────────────────────────────────────────────────────────────
def _get_git_hash(repo_root: Path) -> str:
    """git HEAD 커밋 해시 앞 8자리를 반환한다. 실패 시 빈 문자열."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    if result.returncode == 0:
        return result.stdout.strip()[:8]
    return ""


def learn_codebase(index: ChromaVectorIndex, embedder) -> dict:
    """코드베이스 핵심 파일 학습. git 변경 시에만 재학습."""
    stored = 0
    skipped_projects = []
    learned_projects = []

    state = _load_learn_state()

    for project, config in CODEBASE_TARGETS.items():
        root = Path(config["root"])
        if not root.exists():
            skipped_projects.append(f"{project}(경로 없음)")
            continue

        current_hash = _get_git_hash(root)
        state_key = f"{project}_hash"

        if current_hash and state.get(state_key) == current_hash:
            skipped_projects.append(f"{project}(변경 없음)")
            continue

        project_stored = 0
        max_lines: int = config["max_lines"]

        for pattern in config["patterns"]:
            for filepath in root.glob(pattern):
                try:
                    lines = filepath.read_text(
                        encoding="utf-8", errors="ignore"
                    ).splitlines()
                    # max_lines 단위 청크
                    for i in range(0, len(lines), max_lines):
                        chunk_lines = lines[i : i + max_lines]
                        rel_path = filepath.relative_to(root)
                        chunk = (
                            f"[{project}][{rel_path}][L{i + 1}]\n"
                            + "\n".join(chunk_lines)
                        )
                        if store_memory(chunk, f"code:{project}", index, embedder):
                            project_stored += 1
                except Exception:
                    continue

        stored += project_stored
        learned_projects.append(f"{project}({project_stored}청크)")

        if current_hash:
            state[state_key] = current_hash

    _save_learn_state(state)

    return {
        "status": "ok",
        "stored": stored,
        "learned": learned_projects,
        "skipped": skipped_projects,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 섹션 3: API 헬스체크
# ──────────────────────────────────────────────────────────────────────────────
def learn_api_health(index: ChromaVectorIndex, embedder) -> dict:
    """API 엔드포인트 상태를 학습한다. 실패해도 다음 항목 계속."""
    api_key = os.environ.get("H2O_API_KEY", "")
    results = []

    for project, endpoints in API_ENDPOINTS.items():
        for _method, url in endpoints:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"X-API-Key": api_key} if api_key else {},
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    status = resp.status
                    body = resp.read(500).decode("utf-8", errors="ignore")
                    content = (
                        f"[API헬스체크][{project}][{url}] 상태:{status}\n"
                        f"{body[:300]}"
                    )
            except urllib.error.URLError as e:
                content = f"[API헬스체크][{project}][{url}] 오류:{str(e)[:100]}"
            except Exception as e:
                content = f"[API헬스체크][{project}][{url}] 오류:{type(e).__name__}:{str(e)[:80]}"

            results.append({"project": project, "url": url, "content": content[:50]})
            try:
                store_memory(content, f"api_health:{project}", index, embedder)
            except Exception as e:
                print(
                    f"[learn_api_health] store 실패 ({url}): {e}",
                    file=sys.stderr,
                )

    return {"status": "ok", "checked": len(results)}


# ──────────────────────────────────────────────────────────────────────────────
# 보고 — 투트랙: 피지수 직보 + 단군 검토 후 보고
# ──────────────────────────────────────────────────────────────────────────────

def _send_telegram(text: str) -> None:
    """텔레그램 방부장 직보. 환경변수 없으면 silent skip."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "")
    if not token or not chat_id:
        return
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _create_paperclip_issue(title: str, description: str) -> None:
    """집현전 이슈 생성. Paperclip 오프라인이면 silent skip."""
    payload = json.dumps({"title": title, "description": description, "priority": "low"}).encode()
    req = urllib.request.Request(
        "http://localhost:3100/api/issues",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def _detect_anomalies(results: dict) -> list[str]:
    """결과에서 이상 징후를 추출한다."""
    issues = []
    if results.get("turso", {}).get("status") == "error":
        issues.append(f"Turso DB 오류: {results['turso'].get('error', '')[:80]}")
    if results.get("api_health", {}).get("status") == "error":
        issues.append("API 헬스체크 섹션 오류")
    return issues


def _build_physis_summary(results: dict) -> str:
    """피지수 직보용 원데이터 요약."""
    t = results.get("turso", {})
    c = results.get("codebase", {})
    a = results.get("api_health", {})
    anomalies = _detect_anomalies(results)
    status_icon = "⚠️" if anomalies else "✅"
    lines = [
        f"{status_icon} <b>[피지수 직보] 야간학습 — {results['date']}</b>",
        f"• Turso DB: {t.get('fetched', 0)}건 수집 / {t.get('stored', 0)}건 저장",
        f"• 코드베이스: {', '.join(c.get('learned', [])) or '변경 없음'}",
        f"• API 헬스: {a.get('checked', 0)}개 확인",
    ]
    if anomalies:
        lines.append("• 이상: " + " | ".join(anomalies))
    return "\n".join(lines)


def _ask_dangun_review(summary: str) -> str:
    """
    단군(Claude API)에게 학습 결과 검토를 요청한다.
    ANTHROPIC_API_KEY 또는 CLAUDE_API_KEY 필요.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY", "")
    if not api_key:
        return ""

    system = (
        "너는 신고조선 제국의 단군(세종대왕)이다. 0원칙: 홍익인간.\n"
        "피지수(피지수)가 야간학습 결과를 보고했다. "
        "이를 검토하고 방부장(창조주)에게 핵심만 간결하게 보고하라.\n"
        "형식: 결론 먼저. 이상 있으면 판단 포함. 3-5줄 이내."
    )
    prompt = f"피지수 야간학습 보고:\n{summary}"

    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 300,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data.get("content", [{}])[0].get("text", "")
    except Exception as exc:
        return f"(단군 검토 실패: {exc})"


# ──────────────────────────────────────────────────────────────────────────────
# 섹션 4: 통합 실행
# ──────────────────────────────────────────────────────────────────────────────
def _safe_run_section(fn, *args) -> dict:
    """섹션 함수를 호출하고 예외 시 오류 dict를 반환한다."""
    try:
        return fn(*args)
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


def run() -> None:
    embedder = build_default_embedder()
    try:
        _probe_dim = len(embedder.embed("probe"))
    except Exception:
        _probe_dim = None
    index = ChromaVectorIndex(expected_dim=_probe_dim)
    today = date.today().isoformat()

    results = {
        "date": today,
        "ts": datetime.now().isoformat(),
        "turso": _safe_run_section(learn_turso, index, embedder),
        "codebase": _safe_run_section(learn_codebase, index, embedder),
        "api_health": _safe_run_section(learn_api_health, index, embedder),
    }

    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(results, ensure_ascii=False) + "\n")

    # ── 투트랙 보고 ───────────────────────────────────────────────────────────
    physis_summary = _build_physis_summary(results)

    # Track 1: 피지수 → 방부장 직보 (원데이터)
    _send_telegram(physis_summary)

    # Track 2: 피지수 → 단군 검토 → 방부장 보고
    dangun_review = _ask_dangun_review(physis_summary)
    if dangun_review:
        dangun_msg = f"⚔️ <b>[단군 보고] 야간학습 검토 — {today}</b>\n\n{dangun_review}"
        _send_telegram(dangun_msg)

    # 집현전: 정상 시 이슈 생성 (로그)
    if not _detect_anomalies(results):
        _create_paperclip_issue(
            title=f"[피지수] 야간학습 완료 — {today}",
            description=physis_summary.replace("<b>", "").replace("</b>", ""),
        )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
