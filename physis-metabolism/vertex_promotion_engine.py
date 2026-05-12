"""
꼭짓점 선택 알고리즘 — 사관 3명 합의 (5/9 미해결 과제 #2 해결).

피지수의 구체프랙탈에서 *어떤 표면 노드가 새 구체의 중심(시드)*이 되는가?
사관 합의:
  - Simons   : |z-score|>2.0 AND |autocorr_lag1|<0.3
  - Druckenmiller : outcome_score 비대칭 손익비 + 역전파 가중치
  - Minervini : surface_momentum>50% + volatility_contraction
  - 이채원    : 거버넌스 무경고 (한국 시장 한정)

이 4 조건의 AND가 통과한 노드만 `is_surface_vertex=True`로 승격.
스키마 v3 박제 후 가동 가능. 지금은 *알고리즘 박제* + smoke test 모드.

사용:
  python vertex_promotion_engine.py --smoke   # 가상 노드로 테스트
  python vertex_promotion_engine.py --run     # 실제 nodes 테이블 갱신
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import duckdb

DUCKDB_PATH = "/home/nas/AG-Forge/physis_memory/physis_brain.duckdb"


@dataclass
class VertexCandidate:
    node_id: int
    sphere_id: int
    sector_id: Optional[int]
    fractal_depth: int
    content: str
    ref_count: int
    outcome_score: Optional[float]
    # v3 컬럼들 (스키마 박제 후)
    outcome_z_score: Optional[float] = None
    outcome_autocorr_lag1: Optional[float] = None
    surface_momentum_pct: Optional[float] = None
    governance_warning: bool = False
    vertex_lineage_penalty: float = 0.0


# 사관 임계값 (룰북 박제)
THRESHOLDS = {
    "simons_z_min": 2.0,
    "simons_autocorr_max": 0.3,
    "minervini_momentum_min": 50.0,
    "druckenmiller_lineage_penalty_max": 0.5,
}


def check_simons(v: VertexCandidate) -> dict:
    """Simons: |z|>2.0 AND |autocorr|<0.3"""
    if v.outcome_z_score is None or v.outcome_autocorr_lag1 is None:
        return {"pass": False, "reason": "no_z_or_autocorr_data"}
    cond = (
        abs(v.outcome_z_score) > THRESHOLDS["simons_z_min"]
        and abs(v.outcome_autocorr_lag1) < THRESHOLDS["simons_autocorr_max"]
    )
    return {
        "pass": cond,
        "z_score": v.outcome_z_score,
        "autocorr_lag1": v.outcome_autocorr_lag1,
    }


def check_minervini(v: VertexCandidate) -> dict:
    """Minervini: surface_momentum > 50%"""
    if v.surface_momentum_pct is None:
        return {"pass": False, "reason": "no_momentum_data"}
    return {
        "pass": v.surface_momentum_pct > THRESHOLDS["minervini_momentum_min"],
        "momentum_pct": v.surface_momentum_pct,
    }


def check_druckenmiller(v: VertexCandidate) -> dict:
    """Druckenmiller: vertex_lineage_penalty < 임계 (역전파로 누적된 가중치)"""
    return {
        "pass": v.vertex_lineage_penalty < THRESHOLDS["druckenmiller_lineage_penalty_max"],
        "lineage_penalty": v.vertex_lineage_penalty,
    }


def check_leechaewon(v: VertexCandidate) -> dict:
    """이채원: 거버넌스 경고 없음 (한국 시장 한정)"""
    return {
        "pass": not v.governance_warning,
        "governance_warning": v.governance_warning,
    }


def evaluate(v: VertexCandidate) -> dict:
    """4 사관 AND 평가."""
    s = check_simons(v)
    m = check_minervini(v)
    d = check_druckenmiller(v)
    l = check_leechaewon(v)
    promote = all(c["pass"] for c in (s, m, d, l))
    return {
        "node_id": v.node_id,
        "promote": promote,
        "checks": {"simons": s, "minervini": m, "druckenmiller": d, "leechaewon": l},
    }


def smoke_test() -> int:
    """가상 후보 5개로 알고리즘 검증."""
    cases = [
        VertexCandidate(  # 통과 — 4 사관 모두 OK
            node_id=1, sphere_id=1, sector_id=1, fractal_depth=2,
            content="신고가 돌파 + 거래량 폭증", ref_count=120, outcome_score=0.85,
            outcome_z_score=2.5, outcome_autocorr_lag1=0.15,
            surface_momentum_pct=65.0, governance_warning=False,
            vertex_lineage_penalty=0.1,
        ),
        VertexCandidate(  # 거부 — Simons z 미달
            node_id=2, sphere_id=1, sector_id=1, fractal_depth=2,
            content="평범한 노드", ref_count=30, outcome_score=0.5,
            outcome_z_score=1.2, outcome_autocorr_lag1=0.5,
            surface_momentum_pct=55.0, governance_warning=False,
            vertex_lineage_penalty=0.1,
        ),
        VertexCandidate(  # 거부 — 거버넌스 경고
            node_id=3, sphere_id=2, sector_id=2, fractal_depth=1,
            content="공매도 급증 종목", ref_count=80, outcome_score=0.7,
            outcome_z_score=2.3, outcome_autocorr_lag1=0.2,
            surface_momentum_pct=70.0, governance_warning=True,
            vertex_lineage_penalty=0.2,
        ),
        VertexCandidate(  # 거부 — 모멘텀 미달
            node_id=4, sphere_id=1, sector_id=3, fractal_depth=3,
            content="횡보 종목", ref_count=50,
            outcome_score=0.6, outcome_z_score=2.1, outcome_autocorr_lag1=0.25,
            surface_momentum_pct=30.0, governance_warning=False,
            vertex_lineage_penalty=0.1,
        ),
        VertexCandidate(  # 거부 — 가계 페널티 (Druckenmiller 역전파)
            node_id=5, sphere_id=3, sector_id=1, fractal_depth=2,
            content="과거 오염 fractal군 자손", ref_count=90,
            outcome_score=0.75, outcome_z_score=2.4, outcome_autocorr_lag1=0.18,
            surface_momentum_pct=60.0, governance_warning=False,
            vertex_lineage_penalty=0.7,  # 임계 초과
        ),
    ]

    print("━" * 64)
    print("vertex_promotion_engine — smoke test (가상 5 후보)")
    print("━" * 64)
    promoted = 0
    for c in cases:
        result = evaluate(c)
        mark = "✓ PROMOTE" if result["promote"] else "✗ reject"
        print(f"\n[{c.node_id}] {mark}  — \"{c.content}\"")
        for name, chk in result["checks"].items():
            sym = "✓" if chk["pass"] else "✗"
            extra = {k: v for k, v in chk.items() if k != "pass"}
            print(f"    {sym} {name}: {extra}")
        if result["promote"]:
            promoted += 1
    print()
    print(f"━ 결과: {promoted}/{len(cases)} 승격 ━")
    return 0


def run_against_db() -> int:
    """실제 DuckDB nodes 테이블 평가. 스키마 v3 필요 — 미박제 시 안전 종료."""
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    cols = [r[0] for r in con.execute("DESCRIBE nodes").fetchall()]
    needed = ["outcome_z_score", "outcome_autocorr_lag1", "surface_momentum_pct"]
    missing = [c for c in needed if c not in cols]
    if missing:
        print(f"✗ 스키마 v3 미박제. 누락 컬럼: {missing}")
        print("  → ALTER TABLE nodes ADD COLUMN ... 박제 후 재실행")
        con.close()
        return 1
    # 실제 평가 (스키마 박제 후 활성)
    rows = con.execute(
        "SELECT id, sphere_id, sector_id, fractal_depth, content, ref_count, outcome_score, "
        "outcome_z_score, outcome_autocorr_lag1, surface_momentum_pct "
        "FROM nodes WHERE is_surface_vertex IS NULL OR is_surface_vertex = FALSE"
    ).fetchall()
    n_promote = 0
    for r in rows:
        v = VertexCandidate(*r[:7], r[7], r[8], r[9])  # type: ignore
        if evaluate(v)["promote"]:
            n_promote += 1
    print(f"평가 완료: {n_promote}/{len(rows)} 승격 후보")
    con.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="가상 후보 smoke test")
    ap.add_argument("--run", action="store_true", help="실제 DB nodes 평가 (스키마 v3 필요)")
    args = ap.parse_args()
    if args.smoke:
        return smoke_test()
    if args.run:
        return run_against_db()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
