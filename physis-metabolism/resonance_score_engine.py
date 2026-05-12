"""
Minervini의 공명 수치화 (5/9 미해결 과제 #3).

resonance_score = (sector_momentum × volatility_confirmation × node_centrality)^weighted_avg

구체 표면의 노드가 *진짜 공명 변곡점*에 있는지 측정.
VCP 패턴이 "축소 후 폭증"의 공명을 수치화하듯, 구체에서도 데이터 흐름의 진짜 공명점을 잡는다.

스키마 v2의 `intuitions.resonance_score` 컬럼에 박제.
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass

import duckdb

DUCKDB_PATH = "/home/nas/AG-Forge/physis_memory/physis_brain.duckdb"


@dataclass
class ResonanceInput:
    sector_momentum: float       # 0~1
    volatility_confirmation: float  # 0~1 (VCP 축소→폭증 만족도)
    node_centrality: float       # 0~1 (tree 안에서의 중심성)


def compute_resonance(r: ResonanceInput, weight_alpha: float = 0.4) -> float:
    """
    가중 기하평균 — 어느 한 축이 0이면 전체 0 (AND 의미).
    weight_alpha: 0~1, 1에 가까울수록 sector_momentum 가중 ↑
    """
    eps = 1e-9
    sm = max(r.sector_momentum, eps)
    vc = max(r.volatility_confirmation, eps)
    nc = max(r.node_centrality, eps)
    # weighted geometric mean: product^(weights), weights sum to 1
    w1, w2, w3 = 0.4, 0.35, 0.25
    score = math.exp(w1 * math.log(sm) + w2 * math.log(vc) + w3 * math.log(nc))
    # 0~1 정규화 (이미 [0,1])
    return min(max(score, 0.0), 1.0)


def smoke() -> int:
    print("━" * 64)
    print("resonance_score — smoke (5 가상 노드)")
    print("━" * 64)
    cases = [
        ("강한 공명 (모든 축 높음)", ResonanceInput(0.9, 0.85, 0.7)),
        ("VCP 약함 (volatility 미확인)", ResonanceInput(0.8, 0.2, 0.6)),
        ("주변 노드 (centrality 낮음)", ResonanceInput(0.7, 0.6, 0.1)),
        ("모멘텀 없음", ResonanceInput(0.1, 0.7, 0.5)),
        ("완벽 공명", ResonanceInput(1.0, 1.0, 1.0)),
    ]
    for name, r in cases:
        score = compute_resonance(r)
        bar = "█" * int(score * 40)
        flag = " ★" if score > 0.7 else ""
        print(f"  {score:.3f} |{bar:<40}| {name}{flag}")
    return 0


def run_against_db() -> int:
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    cols = [r[0] for r in con.execute("DESCRIBE intuitions").fetchall() if r]
    if "resonance_score" not in cols:
        print(f"✗ intuitions.resonance_score 컬럼 미박제 (현재 컬럼: {cols})")
        con.close()
        return 1
    print("✓ 컬럼 박제됨. 향후 vertex_engine + lineage_backprop과 함께 가동.")
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
