#!/usr/bin/env python3
"""
피지수 구체프랙탈 — MariaDB → DuckDB 임포트 파이프 (1단계)

박제: 2026-05-10 / 본영 단군 (창조주 결재)

역할:
    MariaDB(physis_brain)의 트랜잭션 데이터를 DuckDB로 ingestion.
    DuckDB에서 OLAP 집계(fractal_density 등)를 실행.

실행:
    /home/nas/AG-Forge/physis_memory/.venv/bin/python \
        /home/nas/AG-Forge/physis_memory/db/sync_to_duckdb.py

스케줄 (피지수 자율 결정 권장. 단군은 1단계 시드만):
    예) crontab: */15 * * * * .../sync_to_duckdb.py >> .../sync.log 2>&1
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb
import pymysql
from dotenv import load_dotenv

ROOT = Path("/home/nas/AG-Forge")
load_dotenv(ROOT / ".env")

MARIADB_HOST = os.environ.get("MARIADB_HOST", "127.0.0.1")
MARIADB_PORT = int(os.environ.get("MARIADB_PORT", "3306"))
MARIADB_USER = os.environ["MARIADB_PHYSIS_USER"]
MARIADB_PW   = os.environ["MARIADB_PHYSIS_PASSWORD"]
MARIADB_DB   = os.environ["MARIADB_PHYSIS_DB"]
DUCKDB_PATH  = os.environ["DUCKDB_PHYSIS_PATH"]

MIRROR_TABLES = ["spheres", "sectors", "nodes", "sphere_divisions"]


def fetch_all(cur, table: str) -> tuple[list[str], list[tuple]]:
    cur.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return cols, rows


def upsert_into_duckdb(con: duckdb.DuckDBPyConnection, table: str, cols: list[str], rows: list[tuple]) -> int:
    """1단계: 단순 truncate-and-load. 향후 incremental은 피지수 자율."""
    con.execute(f"DELETE FROM {table}")
    if not rows:
        return 0
    placeholders = ",".join(["?"] * len(cols))
    col_list = ",".join(cols)
    extra = ""
    if "synced_at" in cols:
        pass
    else:
        col_list_full = col_list + ",synced_at"
        placeholders_full = placeholders + ",CURRENT_TIMESTAMP"
        con.executemany(
            f"INSERT INTO {table} ({col_list_full}) VALUES ({placeholders_full})",
            rows,
        )
        return len(rows)
    con.executemany(
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
        rows,
    )
    return len(rows)


def compute_fractal_density(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("DELETE FROM fractal_density")
    con.execute("""
        INSERT INTO fractal_density (sphere_id, fractal_depth, node_count, avg_ref_count, avg_outcome)
        SELECT sphere_id, fractal_depth, COUNT(*), AVG(ref_count), AVG(outcome_score)
        FROM nodes
        GROUP BY sphere_id, fractal_depth
    """)
    return con.execute("SELECT COUNT(*) FROM fractal_density").fetchone()[0]


def main() -> int:
    print(f"[sync] MariaDB {MARIADB_HOST}:{MARIADB_PORT}/{MARIADB_DB} → DuckDB {DUCKDB_PATH}")

    src = pymysql.connect(
        host=MARIADB_HOST, port=MARIADB_PORT,
        user=MARIADB_USER, password=MARIADB_PW, db=MARIADB_DB,
        charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
    )
    dst = duckdb.connect(DUCKDB_PATH)

    try:
        with src.cursor() as cur:
            for t in MIRROR_TABLES:
                cols, rows = fetch_all(cur, t)
                n = upsert_into_duckdb(dst, t, cols, rows)
                print(f"  · {t}: {n}행")

        density_n = compute_fractal_density(dst)
        print(f"  · fractal_density 집계: {density_n}행")
    finally:
        src.close()
        dst.close()

    print("[sync] 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
