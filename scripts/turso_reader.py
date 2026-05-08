"""
POPEYEs Turso DB 리더 — turso_reader.py
POPEYEs(H2OWIND_2) 현장 데이터를 Turso libSQL에서 읽어온다.

환경변수:
    POPEYS_DATABASE_URL: libsql://... 형식의 Turso DB URL
    POPEYS_AUTH_TOKEN:   Turso 인증 토큰
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any


async def _fetch_async(date: str) -> dict[str, Any]:
    """비동기 Turso 쿼리 실행."""
    from libsql_client import create_client  # type: ignore

    url = os.environ.get("POPEYS_DATABASE_URL", "")
    token = os.environ.get("POPEYS_AUTH_TOKEN", "")

    if not url:
        print("[turso_reader] POPEYS_DATABASE_URL이 설정되지 않았습니다.", file=sys.stderr)
        return {
            "date": date,
            "team_reports": [],
            "master_summary": None,
            "total_workers": 0,
        }

    async with create_client(url=url, auth_token=token) as client:
        # TeamReport 조회
        team_rs = await client.execute(
            "SELECT id, teamName, content, manualWorkerCount, status "
            "FROM TeamReport WHERE date = ?",
            [date],
        )
        team_reports = [
            {
                "team": str(row[1]) if row[1] is not None else "",
                "content": str(row[2]) if row[2] is not None else "",
                "worker_count": int(row[3]) if row[3] is not None else 0,
                "status": str(row[4]) if row[4] is not None else "",
            }
            for row in team_rs.rows
        ]

        # MasterReport 조회
        master_rs = await client.execute(
            "SELECT workSummary FROM MasterReport WHERE date = ?",
            [date],
        )
        master_summary: str | None = None
        if master_rs.rows:
            val = master_rs.rows[0][0]
            master_summary = str(val) if val is not None else None

    total_workers = sum(r["worker_count"] for r in team_reports)

    return {
        "date": date,
        "team_reports": team_reports,
        "master_summary": master_summary,
        "total_workers": total_workers,
    }


def fetch_popeys_daily(date: str) -> dict[str, Any]:
    """
    주어진 날짜의 POPEYEs 현장 데이터를 Turso에서 읽어온다.

    Args:
        date: 조회할 날짜 (YYYY-MM-DD)

    Returns:
        {
            "date": str,
            "team_reports": [{"team": str, "content": str, "worker_count": int, "status": str}],
            "master_summary": str | None,
            "total_workers": int,
        }

    Note:
        DB 연결 실패 시 빈 결과를 반환하고 stderr에 오류를 기록한다.
    """
    if not date.strip():
        print("[turso_reader] date는 비어있을 수 없습니다.", file=sys.stderr)
        return {
            "date": date,
            "team_reports": [],
            "master_summary": None,
            "total_workers": 0,
        }

    try:
        return asyncio.run(_fetch_async(date.strip()))
    except Exception as exc:
        print(f"[turso_reader] Turso 조회 실패: {type(exc).__name__}: {exc}", file=sys.stderr)
        return {
            "date": date,
            "team_reports": [],
            "master_summary": None,
            "total_workers": 0,
        }
