"""
신고조선 메시지 버스 — messaging.py
N:N 비동기 통신 인프라 (Store-and-forward + Optimistic delivery).

설계 원칙:
  1. 모든 메시지 → Turso `imperial_messages` 테이블에 1차 영구 저장 (손실 0)
  2. 상대 살아있으면 → HTTP push로 즉시 응답 (선택적 가속)
  3. 상대 자고있으면 → 깨어날 때 polling으로 발견 → 처리

방부장 칙령 2026-04-30: "1차 디비, 깨어있으면 1번 방법으로 통신, 자고있으면 디비로 깨운다."

stdlib만 사용 (urllib + json) — venv-agnostic. 어느 에이전트 venv에서도 import 가능.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    _ROOT = Path(__file__).parent
    load_dotenv(_ROOT / ".env")
    load_dotenv(_ROOT / ".env.local", override=True)
except ImportError:
    pass


# ── 에이전트 HTTP 엔드포인트 (선택적 가속 채널) ────────────────────────
AGENT_HTTP_ENDPOINTS: dict[str, str] = {
    "dangun": "http://localhost:8020",
    "physis": "http://localhost:8010",
}


def _turso_pipeline(stmts: list[dict]) -> dict:
    """Turso HTTP API에 SQL 파이프라인 실행."""
    raw_url = os.environ.get("DATABASE_URL", "")
    if "?authToken=" not in raw_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    base_url, token = raw_url.split("?authToken=", 1)
    base_url = base_url.replace("libsql://", "https://")

    payload = json.dumps({"requests": stmts + [{"type": "close"}]}).encode()
    req = urllib.request.Request(
        f"{base_url}/v2/pipeline",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _q(s: str) -> str:
    """SQL 문자열 이스케이프."""
    return s.replace("'", "''")


def _is_alive(agent: str, timeout_ms: int = 200) -> bool:
    """상대 에이전트 HTTP 서버가 살아있는지 빠르게 확인."""
    endpoint = AGENT_HTTP_ENDPOINTS.get(agent)
    if not endpoint:
        return False
    try:
        with urllib.request.urlopen(f"{endpoint}/health", timeout=timeout_ms / 1000):
            return True
    except Exception:
        return False


def send_message(
    from_agent: str,
    to_agent: str,
    message: str,
    *,
    thread_id: str | None = None,
    priority: str = "normal",
    try_realtime: bool = True,
) -> dict:
    """
    메시지를 보낸다. 1차 DB 저장 → 2차 HTTP 시도(상대 깨어있으면).

    Returns:
        {"id": str, "status": "pending"|"replied", "response": str|None, "delivery": "db"|"http"}
    """
    msg_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    thread_clause = f"'{_q(thread_id)}'" if thread_id else "NULL"
    sql = (
        f"INSERT INTO imperial_messages "
        f"(id, from_agent, to_agent, message, status, thread_id, priority, created_at) "
        f"VALUES ('{msg_id}', '{_q(from_agent)}', '{_q(to_agent)}', '{_q(message)}', "
        f"'pending', {thread_clause}, '{_q(priority)}', '{now}')"
    )
    _turso_pipeline([{"type": "execute", "stmt": {"sql": sql}}])

    if try_realtime and _is_alive(to_agent):
        try:
            endpoint = AGENT_HTTP_ENDPOINTS[to_agent]
            payload = json.dumps({"issue": message}).encode()
            req = urllib.request.Request(
                f"{endpoint}/api/dangun_brain" if to_agent == "dangun" else f"{endpoint}/api/task",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                response_text = data.get("result") or data.get("response") or json.dumps(data, ensure_ascii=False)
                replied_at = datetime.now().isoformat()
                update_sql = (
                    f"UPDATE imperial_messages SET response='{_q(response_text)}', "
                    f"status='replied', replied_at='{replied_at}' WHERE id='{msg_id}'"
                )
                _turso_pipeline([{"type": "execute", "stmt": {"sql": update_sql}}])
                return {"id": msg_id, "status": "replied", "response": response_text, "delivery": "http"}
        except Exception:
            pass

    return {"id": msg_id, "status": "pending", "response": None, "delivery": "db"}


def poll_inbox(agent: str, limit: int = 10) -> list[dict]:
    """내 앞으로 온 미처리 메시지를 가져온다."""
    sql = (
        f"SELECT id, from_agent, message, thread_id, priority, created_at "
        f"FROM imperial_messages "
        f"WHERE to_agent='{_q(agent)}' AND status='pending' "
        f"ORDER BY CASE priority WHEN 'emergency' THEN 0 WHEN 'high' THEN 1 ELSE 2 END, created_at "
        f"LIMIT {int(limit)}"
    )
    data = _turso_pipeline([{"type": "execute", "stmt": {"sql": sql}}])
    res = data.get("results", [{}])[0]
    if res.get("type") == "error":
        return []
    rows = res.get("response", {}).get("result", {}).get("rows", [])
    return [
        {
            "id": r[0]["value"],
            "from": r[1]["value"],
            "message": r[2]["value"],
            "thread_id": r[3].get("value"),
            "priority": r[4]["value"],
            "created_at": r[5]["value"],
        }
        for r in rows
    ]


def reply_message(message_id: str, response: str) -> dict:
    """메시지에 응답을 기록한다 (status: pending → replied)."""
    replied_at = datetime.now().isoformat()
    sql = (
        f"UPDATE imperial_messages SET response='{_q(response)}', "
        f"status='replied', replied_at='{replied_at}' WHERE id='{_q(message_id)}'"
    )
    _turso_pipeline([{"type": "execute", "stmt": {"sql": sql}}])
    return {"id": message_id, "status": "replied", "replied_at": replied_at}


def fetch_replies(from_agent: str, since: str | None = None, limit: int = 10) -> list[dict]:
    """내가 보낸 메시지 중 응답이 도착한 것을 가져온다."""
    where_extra = f" AND replied_at > '{_q(since)}'" if since else ""
    sql = (
        f"SELECT id, to_agent, message, response, replied_at "
        f"FROM imperial_messages "
        f"WHERE from_agent='{_q(from_agent)}' AND status='replied'{where_extra} "
        f"ORDER BY replied_at DESC LIMIT {int(limit)}"
    )
    data = _turso_pipeline([{"type": "execute", "stmt": {"sql": sql}}])
    res = data.get("results", [{}])[0]
    if res.get("type") == "error":
        return []
    rows = res.get("response", {}).get("result", {}).get("rows", [])
    return [
        {
            "id": r[0]["value"],
            "to": r[1]["value"],
            "message": r[2]["value"],
            "response": r[3]["value"],
            "replied_at": r[4]["value"],
        }
        for r in rows
    ]
