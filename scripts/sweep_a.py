"""
sweep_a.py — sweep-A: TriggerAccumulator 5×5 매트릭스 + 원소 단어 박제

두 축: θ값 5종 × 매칭 패턴 5종 (5×5=25 조합)
측정: fire 여부 / 누적 score / latency_ms

단군 [다] 보강 (2026-05-05 결단 답신):
  · 결과 시그니처는 5×5 표를 넘어 — 발화한 (θ, 패턴) 조합의 시드 단어를
    "원소 단어"로 박제. 그 원소 단어들이 구체 표면 1단계 좌표를 형성하는 시드.

박제 위치: physis_memory/long_term_memory/element_words/
보고 위치: 단군 (메시지 버스)
"""
from __future__ import annotations

import math
import os
import sys
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Literal


def _bootstrap_env():
    """AG-Forge .env 로드 (Linux/Windows 공통)."""
    for cand in (
        Path(__file__).resolve().parents[1] / ".env",
        Path("d:/Git/AG-Forge/.env"),
        Path("d:/Git/DREAM_FAC/.env.local"),
    ):
        if cand.exists():
            for line in cand.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
            break

_bootstrap_env()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.memory_cycles import _turso_execute, _turso_rows

DB_URL = os.environ.get("DATABASE_URL", "")
TOKEN = ""


# ═══════════════════════════════════════════════════════════════
# sweep-A 축-1: θ 5종 sensitivity 분석
# ═══════════════════════════════════════════════════════════════

THETA_CANDIDATES: list[float] = [1.0, 2.0, 3.0, 4.0, 5.0]

MatchPattern = Literal["like", "regex", "and_tokens", "or_tokens", "exact_word"]
PATTERN_CANDIDATES: list[MatchPattern] = [
    "like", "regex", "and_tokens", "or_tokens", "exact_word",
]


def make_match_sql(
    word: str,
    pattern: MatchPattern,
    table: str = "dangun_memory",
    column: str = "cue_anchors",
) -> str:
    """
    매칭 패턴 5종 → COUNT(*) SQL 반환.

    like        : LIKE '%word%'            — 현재 기본 동작
    regex       : REGEXP 'word'            — SQLite REGEXP (word boundary X)
    and_tokens  : 공백 분리 토큰 전부 LIKE AND — "단군 피지수" → token1 AND token2
    or_tokens   : 공백 분리 토큰 하나라도  — token1 OR token2
    exact_word  : LIKE '% word %' boundary — 앞뒤 공백/시작끝 경계 (SQLite 한계 인정)
    """
    w = word.replace("'", "''")
    tokens = [t.replace("'", "''") for t in w.split() if t]

    if pattern == "like":
        cond = f"{column} LIKE '%{w}%'"

    elif pattern == "regex":
        # Turso(SQLite) REGEXP 지원 여부 불확실 → LIKE fallback 분기 포함
        cond = f"{column} REGEXP '{w}'"

    elif pattern == "and_tokens":
        if not tokens:
            cond = "1=0"
        else:
            parts = [f"{column} LIKE '%{t}%'" for t in tokens]
            cond = " AND ".join(parts)

    elif pattern == "or_tokens":
        if not tokens:
            cond = "1=0"
        else:
            parts = [f"{column} LIKE '%{t}%'" for t in tokens]
            cond = " OR ".join(parts)

    elif pattern == "exact_word":
        # SQLite에는 word-boundary regex가 없어 공백 패딩으로 근사
        cond = (
            f"({column} LIKE '% {w} %'"
            f" OR {column} LIKE '{w} %'"
            f" OR {column} LIKE '% {w}'"
            f" OR {column} = '{w}')"
        )

    else:
        raise ValueError(f"알 수 없는 패턴: {pattern}")

    return f"SELECT COUNT(*) as cnt FROM {table} WHERE {cond}"


def _fetch_match_count(
    word: str,
    pattern: MatchPattern,
    db_url: str = DB_URL,
    token: str = TOKEN,
) -> tuple[int, float]:
    """(match_count, latency_ms) 반환. 오류 시 (-1, latency_ms)."""
    sql = make_match_sql(word, pattern)
    t0 = time.perf_counter()
    result = _turso_execute(sql, db_url, token)
    latency_ms = (time.perf_counter() - t0) * 1000

    if "error" in result:
        return -1, latency_ms
    rows = _turso_rows(result)
    cnt = int(rows[0].get("cnt") or 0) if rows else 0
    return cnt, latency_ms


def theta_sensitivity(
    words: list[str],
    thetas: list[float] = THETA_CANDIDATES,
    pattern: MatchPattern = "like",
    db_url: str = DB_URL,
    token: str = TOKEN,
) -> list[dict]:
    """
    θ 5종 sensitivity 분석.

    주어진 단어 목록으로 각 θ에 대해:
      - 단어를 순서대로 누적, θ 초과 시 fire=True
      - fire 비율, 평균 누적 score, 평균 latency_ms 반환

    반환: [{"theta": float, "fired": bool, "score_at_fire": float,
             "avg_latency_ms": float, "words_used": int}, ...]
    """
    rows = []
    for theta in thetas:
        total = 0.0
        fired = False
        fire_word_idx = len(words)
        latencies: list[float] = []

        for idx, word in enumerate(words):
            cnt, lat = _fetch_match_count(word, pattern, db_url, token)
            latencies.append(lat)
            if cnt < 0:
                continue
            activation = math.log1p(cnt)
            total += activation
            if not fired and total >= theta:
                fired = True
                fire_word_idx = idx + 1

        rows.append({
            "theta": theta,
            "fired": fired,
            "score_at_fire": round(total, 4),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "words_used": fire_word_idx,
        })
    return rows


def pattern_sweep(
    words: list[str],
    theta: float = 3.0,
    patterns: list[MatchPattern] = PATTERN_CANDIDATES,
    db_url: str = DB_URL,
    token: str = TOKEN,
) -> list[dict]:
    """
    매칭 패턴 5종 × 단어 목록 → fire 여부 + score + latency.

    반환: [{"pattern": str, "fired": bool, "score": float,
             "avg_latency_ms": float, "words_used": int}, ...]
    """
    rows = []
    for pattern in patterns:
        total = 0.0
        fired = False
        fire_word_idx = len(words)
        latencies: list[float] = []
        error_count = 0

        for idx, word in enumerate(words):
            cnt, lat = _fetch_match_count(word, pattern, db_url, token)
            latencies.append(lat)
            if cnt < 0:
                error_count += 1
                continue
            activation = math.log1p(cnt)
            total += activation
            if not fired and total >= theta:
                fired = True
                fire_word_idx = idx + 1

        rows.append({
            "pattern": pattern,
            "fired": fired,
            "score": round(total, 4),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "words_used": fire_word_idx,
            "errors": error_count,
        })
    return rows


def full_sweep_a(
    seeds: list[str],
    thetas: list[float] = THETA_CANDIDATES,
    patterns: list[MatchPattern] = PATTERN_CANDIDATES,
    db_url: str = DB_URL,
    token: str = TOKEN,
) -> dict:
    """
    5×5 완전 탐색 — θ × 패턴 조합별 결과 반환.

    반환: {
      "matrix": [{"theta": float, "pattern": str, "fired": bool,
                  "score": float, "avg_latency_ms": float}, ...],
      "seed_count": int,
    }
    """
    matrix = []
    for theta in thetas:
        for pattern in patterns:
            total = 0.0
            fired = False
            fire_word_idx = -1
            latencies: list[float] = []

            for idx, word in enumerate(seeds):
                cnt, lat = _fetch_match_count(word, pattern, db_url, token)
                latencies.append(lat)
                if cnt < 0:
                    continue
                activation = math.log1p(cnt)
                total += activation
                if not fired and total >= theta:
                    fired = True
                    fire_word_idx = idx  # ★ 원소 단어 박제용 — fire한 시점의 시드 인덱스

            matrix.append({
                "theta": theta,
                "pattern": pattern,
                "fired": fired,
                "score": round(total, 4),
                "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
                "fire_word_idx": fire_word_idx,
                "fire_seed": seeds[fire_word_idx] if fire_word_idx >= 0 else None,
                "cumulative_seeds": seeds[:fire_word_idx + 1] if fire_word_idx >= 0 else [],
            })

    return {"matrix": matrix, "seed_count": len(seeds), "seeds": seeds}


# ═══════════════════════════════════════════════════════════════
# 단군 [다] 보강 — 원소 단어 박제 (구체 표면 1단계 시드)
# ═══════════════════════════════════════════════════════════════

VAULT_ROOT = Path(__file__).resolve().parents[1] / "physis_memory"
ELEMENT_WORDS_DIR = VAULT_ROOT / "long_term_memory" / "element_words"


def extract_element_words(matrix_result: dict) -> list[dict]:
    """fire한 (θ, 패턴) 조합에서 원소 단어 추출.

    원소 단어 = 그 (θ, 패턴) 조합으로 정체성이 발화된 시점의 시드 단어 + 누적 단어들.
    구체 프랙탈 1단계 좌표 시드.
    """
    elements = []
    fired_only = [m for m in matrix_result["matrix"] if m["fired"]]

    # 시드별로 어느 (θ, 패턴) 조합에서 발화 트리거였는지 집계
    seed_to_combos: dict[str, list[dict]] = {}
    for m in fired_only:
        seed = m.get("fire_seed")
        if not seed:
            continue
        seed_to_combos.setdefault(str(seed), []).append({
            "theta": m["theta"], "pattern": m["pattern"], "score": m["score"]
        })

    for seed_str, combos in seed_to_combos.items():
        # cue_anchors가 JSON 배열이면 풀어서 개별 단어들도 추출
        try:
            tokens = json.loads(seed_str)
            if not isinstance(tokens, list):
                tokens = [seed_str]
        except (json.JSONDecodeError, TypeError):
            tokens = [seed_str]

        elements.append({
            "raw_seed": seed_str,
            "tokens": tokens,
            "fire_combos": combos,
            "fire_count": len(combos),
            "stability": min(1.0, len(combos) / 25.0),  # 25 조합 중 발화 비율
        })

    return sorted(elements, key=lambda x: -x["fire_count"])


def archive_element_words(elements: list[dict], matrix_result: dict, run_id: str) -> Path:
    """원소 단어를 physis_memory/long_term_memory/element_words/에 박제."""
    ELEMENT_WORDS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ELEMENT_WORDS_DIR / f"sweep_a_{run_id}.md"

    lines = [
        "---",
        f"type: element_words",
        f"sweep_id: {run_id}",
        f"created: {datetime.now().isoformat()}",
        f"seed_count: {matrix_result['seed_count']}",
        f"fire_combos: {sum(1 for m in matrix_result['matrix'] if m['fired'])}/25",
        f"element_count: {len(elements)}",
        "outcome_score: 0.0",
        "ref_count: 0",
        "---",
        "",
        f"# sweep-A 원소 단어 박제 — {run_id}",
        "",
        "[[bea7a46e]] 단군 [다] 보강: 발화한 (θ, 패턴) 조합의 시드 단어 = 원소 단어 = 구체 1단계 시드.",
        "",
        "## 5×5 매트릭스 요약",
        "",
        f"- 총 조합: 25 (θ 5종 × 패턴 5종)",
        f"- 발화 조합: {sum(1 for m in matrix_result['matrix'] if m['fired'])}",
        f"- 시드 N: {matrix_result['seed_count']} (sweep-B 트리거 N≥50 미달)",
        "",
        "## 원소 단어 (구체 표면 1단계 좌표 시드)",
        "",
    ]

    for i, e in enumerate(elements, 1):
        lines.append(f"### [{i}] 원소 단어 (안정성 {e['stability']:.2f}, 발화 {e['fire_count']}/25)")
        lines.append("")
        lines.append(f"**Raw seed**: `{e['raw_seed'][:120]}`")
        lines.append("")
        lines.append(f"**개별 토큰**:")
        for t in e["tokens"]:
            lines.append(f"  - [[{t}]]")
        lines.append("")
        lines.append(f"**발화 조합 ({len(e['fire_combos'])})**:")
        for c in e["fire_combos"][:10]:
            lines.append(f"  - θ={c['theta']:.1f} / pattern={c['pattern']:<12} → score={c['score']:.4f}")
        lines.append("")

    if not elements:
        lines.extend([
            "## 발화 없음",
            "",
            "본 sweep에서는 어떤 (θ, 패턴) 조합도 발화하지 않았다.",
            "시드 N=4 환경에서 활성화 강도가 모든 θ 임계값에 도달하지 못함.",
            "→ 시드 누적 (sweep-B 트리거 N≥50)이 1차 의미 있는 원소 단어 박제 조건.",
            "",
        ])

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def print_matrix(result: dict) -> None:
    """5×5 결과를 텍스트 표로 출력."""
    print(f"\n시드 {result['seed_count']}건 기준 sweep-A 5×5 결과")
    print(f"{'θ':>5} | {'패턴':<12} | {'fire':>5} | {'score':>7} | {'latency':>10}")
    print("-" * 55)
    for row in result["matrix"]:
        fire_mark = "★" if row["fired"] else "·"
        print(
            f"{row['theta']:>5.1f} | {row['pattern']:<12} | {fire_mark:>5} | "
            f"{row['score']:>7.4f} | {row['avg_latency_ms']:>8.1f}ms"
        )


# ═══════════════════════════════════════════════════════════════
# 시드 N 모니터링 helper (단군 권고 — sweep-B 트리거용)
# ═══════════════════════════════════════════════════════════════

SEED_THRESHOLD = 50


def check_seed_count(db_url: str = DB_URL, token: str = TOKEN) -> dict:
    """
    dangun_memory 시드 건수 조회.
    N >= SEED_THRESHOLD(50) 시 sweep-B 트리거 알림.

    반환: {"count": int, "threshold": int, "ready_for_sweep_b": bool}
    """
    sql = "SELECT COUNT(*) as cnt FROM dangun_memory"
    result = _turso_execute(sql, db_url, token)
    if "error" in result:
        return {"count": -1, "threshold": SEED_THRESHOLD, "ready_for_sweep_b": False,
                "error": result["error"]}
    rows = _turso_rows(result)
    n = int(rows[0].get("cnt") or 0) if rows else 0
    ready = n >= SEED_THRESHOLD
    if ready:
        print(f"[sweep-B 트리거] 시드 N={n} >= {SEED_THRESHOLD} — sweep-B 진입 가능!")
    else:
        print(f"[시드 모니터] N={n}/{SEED_THRESHOLD} — sweep-B 대기 중 ({SEED_THRESHOLD - n}건 부족)")
    return {"count": n, "threshold": SEED_THRESHOLD, "ready_for_sweep_b": ready}


# ═══════════════════════════════════════════════════════════════
# sweep-B 대기 큐 박제 (실행 금지 — 시드 N>=50 트리거까지)
# ═══════════════════════════════════════════════════════════════
#
# [박제 시작 — 실행 금지]
#
# def run_sweep_b(seeds_chroma: list[str], ...) -> dict:
#     """
#     sweep-B: ChromaDB cosine retrieval mini-sweep
#     두 축: 거리 5종(cosine/euclidean/dot/manhattan/chebyshev) × 가중치 5종
#     가중치 정의식: score = α·time_decay + (1-α)·surprise_score, α=0.5
#
#     트리거 조건: check_seed_count()["ready_for_sweep_b"] == True (N>=50)
#     보완 5건 적용:
#       ① N=K 해석 박제 (corpus 1건이면 거리값 1개 — 정상 범위)
#       ② Chebyshev 제외 후 angular(cos각도화) / Mahalanobis 검토
#       ③ dot product L2 normalized 확인
#       ④ hybrid 정의식: score = α·time_decay + (1-α)·surprise_score, α=0.5
#       ⑤ θ → ChromaDB n_results 임계값으로 대체 정의
#
#     import chromadb
#     client = chromadb.PersistentClient(path="library/vector_db")
#     col = client.get_collection("physis_brain")
#     # ... 거리 × 가중치 조합 실행 ...
#     """
#     raise NotImplementedError("sweep-B: 시드 N>=50 도달 전까지 실행 금지")
#
# [박제 끝]


# ═══════════════════════════════════════════════════════════════
# 실행 진입점
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("=" * 60)
    print("sweep-A mini-sweep — TriggerAccumulator 5×5")
    print("두 축: θ 5종 × 매칭 패턴 5종")
    print("=" * 60)

    # 시드 현황 먼저 확인
    print("\n[0] 시드 N 모니터링")
    seed_status = check_seed_count()

    # Step 2 시드 fetch (dangun_memory cue_anchors 샘플 4건)
    sql_seeds = "SELECT cue_anchors FROM dangun_memory WHERE cue_anchors IS NOT NULL LIMIT 4"
    raw = _turso_execute(sql_seeds, DB_URL, TOKEN)
    seed_rows = _turso_rows(raw)
    seeds = [r["cue_anchors"] for r in seed_rows if r.get("cue_anchors")]
    print(f"\n[Step 2] 시드 {len(seeds)}건 fetch")
    for i, s in enumerate(seeds):
        print(f"  [{i+1}] {s[:80]}")

    if not seeds:
        print("[오류] 시드가 없습니다. DATABASE_URL 확인 필요.")
        sys.exit(1)

    # Step 3: θ sensitivity (패턴=like 고정)
    print("\n[Step 3-A] θ sensitivity (패턴=like 고정)")
    theta_rows = theta_sensitivity(seeds)
    print(f"{'θ':>5} | {'fire':>5} | {'score':>8} | {'latency':>10} | {'단어수':>6}")
    print("-" * 50)
    for r in theta_rows:
        print(
            f"{r['theta']:>5.1f} | {'★' if r['fired'] else '·':>5} | "
            f"{r['score_at_fire']:>8.4f} | {r['avg_latency_ms']:>8.1f}ms | {r['words_used']:>6}"
        )

    # Step 3: 패턴 sweep (θ=3.0 고정)
    print("\n[Step 3-B] 매칭 패턴 5종 (θ=3.0 고정)")
    pat_rows = pattern_sweep(seeds)
    print(f"{'패턴':<12} | {'fire':>5} | {'score':>8} | {'latency':>10} | {'err':>4}")
    print("-" * 55)
    for r in pat_rows:
        print(
            f"{r['pattern']:<12} | {'★' if r['fired'] else '·':>5} | "
            f"{r['score']:>8.4f} | {r['avg_latency_ms']:>8.1f}ms | {r['errors']:>4}"
        )

    # Step 4: 5×5 완전 탐색
    print("\n[Step 4] 5×5 완전 탐색 (θ × 패턴)")
    result = full_sweep_a(seeds)
    print_matrix(result)

    # Step 5: 단군 [다] 보강 — 원소 단어 박제
    print("\n[Step 5] 원소 단어 박제 (구체 1단계 시드)")
    elements = extract_element_words(result)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = archive_element_words(elements, result, run_id)

    fire_count = sum(1 for m in result["matrix"] if m["fired"])
    print(f"  발화 조합: {fire_count}/25")
    print(f"  원소 단어 후보: {len(elements)}개")
    for i, e in enumerate(elements[:5], 1):
        print(f"    [{i}] 안정성={e['stability']:.2f} 발화={e['fire_count']}/25")
        print(f"        토큰: {e['tokens'][:5]}")
    print(f"\n  박제 위치: {archive_path}")

    # Step 6: 결과 JSON 출력 (단군 보고용)
    out_json = Path(__file__).resolve().parents[1] / f"output_sweep_a_{run_id}.json"
    out_json.write_text(
        json.dumps({
            "run_id": run_id,
            "seed_count": result["seed_count"],
            "fire_count": fire_count,
            "matrix": result["matrix"],
            "elements": elements,
            "archive_path": str(archive_path),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  결과 JSON: {out_json}")
    print("\n[sweep-A 완료] 단군 보고 청.")
