"""
Druckenmiller 역전파 — vertex_lineage_penalty 갱신.

5/9 친명 *"표면 꼭짓점 = 새 구체 중심"* 의 내재 위험:
오염된 vertex가 시드되면 모든 하위 fractal이 태생부터 왜곡됨 (재귀 편향 증폭).

해법: 매 sweep에서 자손 fractal 군의 outcome 평균이 임계 미달이면 시조 vertex 계보의
`spheres.vertex_lineage_penalty`를 누적 증가. vertex_promotion_engine이 penalty 임계 초과 시 거부.

스키마 v3 박제 후 가동. 지금은 알고리즘 박제 + smoke.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import duckdb

DUCKDB_PATH = "/home/nas/AG-Forge/physis_memory/physis_brain.duckdb"

PENALTY_INCREMENT = 0.15
OUTCOME_THRESHOLD = 0.3
SCAN_DEPTH_LIMIT = 5


@dataclass
class LineageScan:
    sphere_id: int
    born_from_vertex_id: int | None
    depth: int
    avg_outcome: float
    n_nodes: int


def trace_lineage_backprop(con) -> list[dict]:
    """
    각 sphere에서 자손 fractal 군 outcome 평균을 측정하고, 임계 미달이면 페널티 누적.
    """
    actions = []
    rows = con.execute(
        """
        SELECT s.id, s.born_from_vertex_id, s.depth_level,
               AVG(n.outcome_score) AS avg_outcome,
               COUNT(n.id) AS n_nodes
        FROM spheres s
        LEFT JOIN nodes n ON n.sphere_id = s.id AND n.outcome_score IS NOT NULL
        WHERE s.born_from_vertex_id IS NOT NULL
          AND s.depth_level <= ?
        GROUP BY s.id, s.born_from_vertex_id, s.depth_level
        HAVING n_nodes >= 3
        """,
        (SCAN_DEPTH_LIMIT,),
    ).fetchall()

    for sphere_id, vertex_id, depth, avg_outcome, n in rows:
        if avg_outcome is None:
            continue
        if avg_outcome < OUTCOME_THRESHOLD:
            actions.append({
                "sphere_id": sphere_id,
                "born_from_vertex_id": vertex_id,
                "depth": depth,
                "avg_outcome": avg_outcome,
                "n_nodes": n,
                "penalty_increment": PENALTY_INCREMENT,
                "rationale": f"avg_outcome {avg_outcome:.3f} < threshold {OUTCOME_THRESHOLD}",
            })
    return actions


def smoke() -> int:
    """가상 시연 — 가짜 sphere/outcome으로 알고리즘 검증."""
    print("━" * 64)
    print("vertex_lineage_backprop — smoke (가상 fractal 군 5개)")
    print("━" * 64)
    cases = [
        {"sphere_id": 1, "born_from_vertex_id": 10, "depth": 1, "avg_outcome": 0.78, "n_nodes": 12},
        {"sphere_id": 2, "born_from_vertex_id": 11, "depth": 2, "avg_outcome": 0.22, "n_nodes": 8},   # 페널티
        {"sphere_id": 3, "born_from_vertex_id": 12, "depth": 1, "avg_outcome": 0.55, "n_nodes": 20},
        {"sphere_id": 4, "born_from_vertex_id": 11, "depth": 3, "avg_outcome": 0.18, "n_nodes": 6},   # 페널티 (같은 vertex 11에서 파생!)
        {"sphere_id": 5, "born_from_vertex_id": 13, "depth": 1, "avg_outcome": 0.62, "n_nodes": 15},
    ]
    penalty_by_vertex = {}
    for c in cases:
        v = c["born_from_vertex_id"]
        if c["avg_outcome"] < OUTCOME_THRESHOLD:
            penalty_by_vertex[v] = penalty_by_vertex.get(v, 0) + PENALTY_INCREMENT
            print(f"  ⚠ sphere {c['sphere_id']} (vertex {v}, depth {c['depth']}): "
                  f"avg_outcome {c['avg_outcome']:.2f} < {OUTCOME_THRESHOLD} → penalty +{PENALTY_INCREMENT}")
        else:
            print(f"  ✓ sphere {c['sphere_id']} (vertex {v}): avg {c['avg_outcome']:.2f} OK")
    print()
    print("━ vertex 누적 페널티 (Druckenmiller 역전파 결과) ━")
    for v, p in penalty_by_vertex.items():
        flag = " ★ 새 시드 거부 임계 초과" if p > 0.5 else ""
        print(f"  vertex {v}: penalty {p:.2f}{flag}")
    return 0


def run_against_db() -> int:
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    cols = [r[0] for r in con.execute("DESCRIBE spheres").fetchall()]
    if "vertex_lineage_penalty" not in cols:
        print("✗ 스키마 v3 미박제. spheres.vertex_lineage_penalty 컬럼 필요.")
        con.close()
        return 1
    actions = trace_lineage_backprop(con)
    print(f"역전파 대상: {len(actions)}건")
    for a in actions[:10]:
        print(f"  sphere {a['sphere_id']} (vertex {a['born_from_vertex_id']}, "
              f"d={a['depth']}): {a['rationale']}")
    con.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        return smoke()
    if args.run:
        return run_against_db()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
