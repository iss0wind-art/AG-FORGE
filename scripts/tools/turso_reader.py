"""
Turso(LibSQL) 조회 툴.
TeamReport + DailyWorkLog + DailyOutput 에서 오늘 데이터를 읽는다.
"""
import os
from libsql_client import create_client_sync


def _get_client():
    url = os.getenv("TURSO_DATABASE_URL")
    token = os.getenv("TURSO_AUTH_TOKEN")
    if not url:
        raise EnvironmentError("TURSO_DATABASE_URL이 설정되지 않았습니다.")
    return create_client_sync(url=url, auth_token=token)


def fetch_today_team_reports(date: str) -> list[dict]:
    """
    오늘 날짜 TeamReport 목록을 반환한다.
    반환: [{ team, leader, content, manual_worker_count, status }, ...]
    """
    with _get_client() as client:
        rs = client.execute(
            "SELECT teamName, leader, content, manualWorkerCount, status "
            "FROM TeamReport WHERE date = ? ORDER BY teamName",
            [date],
        )
        return [
            {
                "team": row[0],
                "leader": row[1],
                "content": row[2],
                "manual_worker_count": row[3] or 0,
                "status": row[4],
            }
            for row in rs.rows
        ]


def fetch_today_work_logs(date: str) -> list[dict]:
    """
    오늘 날짜 DailyWorkLog를 반환한다.
    반환: [{ team, content, dong, floor, zone_type }, ...]
    """
    with _get_client() as client:
        rs = client.execute(
            "SELECT teamName, content, dong, floor, zoneType "
            "FROM DailyWorkLog WHERE date = ? ORDER BY teamName",
            [date],
        )
        return [
            {
                "team": row[0],
                "content": row[1],
                "dong": row[2],
                "floor": row[3],
                "zone_type": row[4],
            }
            for row in rs.rows
        ]


def fetch_today_daily_output(date: str) -> list[dict]:
    """
    DailyOutput 직종별 집계를 반환한다. (인페이스 집계 원본)
    반환: [{ trade, count }, ...]
    """
    with _get_client() as client:
        rs = client.execute(
            "SELECT trade, count FROM DailyOutput WHERE date = ? ORDER BY trade",
            [date],
        )
        return [{"trade": row[0], "count": float(row[1] or 0)} for row in rs.rows]


def fetch_missing_teams(date: str, all_teams: list[str]) -> list[str]:
    """오늘 보고서를 제출하지 않은 팀 목록을 반환한다."""
    with _get_client() as client:
        rs = client.execute(
            "SELECT teamName FROM TeamReport WHERE date = ?",
            [date],
        )
        reported = {row[0] for row in rs.rows}
    return [t for t in all_teams if t not in reported]
