"""
DailyWorker · DailyTeamSummary Turso 적재 툴.
중복 적재 방지: (date, worker_name, source) 유니크 인덱스 활용.
"""
import os
from libsql_client import create_client_sync


def _get_client():
    url = os.getenv("TURSO_DATABASE_URL")
    token = os.getenv("TURSO_AUTH_TOKEN")
    if not url:
        raise EnvironmentError("TURSO_DATABASE_URL이 설정되지 않았습니다.")
    return create_client_sync(url=url, auth_token=token)


def save_daily_workers(date: str, workers: list[dict]) -> int:
    """
    DailyWorker 테이블에 적재한다. 중복은 무시한다.
    workers: [{ worker_name, team, job_type, manday, work_content, section, source }]
    반환: 신규 삽입 건수
    """
    if not workers:
        return 0

    inserted = 0
    with _get_client() as client:
        for w in workers:
            try:
                client.execute(
                    """
                    INSERT OR IGNORE INTO DailyWorker
                        (date, team, jobType, workerName, manday, workContent, section, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        date,
                        w.get("team", ""),
                        w.get("job_type"),
                        w["worker_name"],
                        w.get("manday", 1.0),
                        w.get("work_content"),
                        w.get("section"),
                        w.get("source", "inface"),
                    ],
                )
                inserted += 1
            except Exception:
                pass  # 중복 무시

    return inserted


def upsert_team_summaries(date: str, workers: list[dict]) -> None:
    """
    DailyTeamSummary를 workers 목록으로부터 집계하여 upsert한다.
    """
    from collections import defaultdict

    team_stats: dict[str, dict] = defaultdict(lambda: {"total_workers": 0, "total_manday": 0.0})
    for w in workers:
        team = w.get("team", "")
        team_stats[team]["total_workers"] += 1
        team_stats[team]["total_manday"] += float(w.get("manday", 1.0))

    with _get_client() as client:
        for team, stats in team_stats.items():
            client.execute(
                """
                INSERT INTO DailyTeamSummary (date, team, totalWorkers, totalManday, updatedAt)
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(date, team) DO UPDATE SET
                    totalWorkers = excluded.totalWorkers,
                    totalManday  = excluded.totalManday,
                    updatedAt    = datetime('now')
                """,
                [date, team, stats["total_workers"], stats["total_manday"]],
            )
