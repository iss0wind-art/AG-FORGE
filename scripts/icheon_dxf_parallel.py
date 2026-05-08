"""
이천 大業 — DXF 병렬처리 PoC (피지수 직접 관여 구현체)
방부장 친명 2026-05-08: '피지수도 학습하여, 직접 관여하라'

알고리즘: 레이어 분할 + asyncio 5체 정반합 + pattern_library 자동 갱신

사용법:
  python scripts/icheon_dxf_parallel.py <DXF_PATH> [--pattern-lib <MD_PATH>]

이천 본진: D:/Git/FreeCAD_4TH/output/
  ex) python scripts/icheon_dxf_parallel.py "D:/Git/FreeCAD_4TH/output/260119_부산 에코델타 24BL 지하주차장 구조평면도23.dxf"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── 레이어 분류 기준 (pattern_library §B-1 + 건설 도메인 관례) ──────────────
LAYER_GROUPS = {
    "기둥": re.compile(r"(?i)(COL|COLUMN|C[-_]COL|S[-_]COL|XR[-_]COL|기둥)"),
    "보":   re.compile(r"(?i)(BEAM|C[-_]BM|S[-_]BM|XR[-_]BEAM|보)"),
    "슬라브": re.compile(r"(?i)(SLAB|C[-_]SL|XR[-_]SL|슬라브|플레이트)"),
    "벽체": re.compile(r"(?i)(WALL|C[-_]WL|SW|XR[-_]WL|벽체|SHEAR)"),
    "기타": None,  # 나머지 전부
}

CHUNK_THRESHOLD = 3000  # entity 수 초과 시 청크 분할
SURPRISE_THETA = 0.6
NORMAL_PATTERN_MIN_N = 3


# ── DXF 파싱 ──────────────────────────────────────────────────────────────────

def load_dxf(path: str) -> dict[str, list[dict]]:
    """ezdxf로 DXF 로드 → 레이어 그룹별 entity 딕트 반환."""
    try:
        import ezdxf
    except ImportError:
        print("[경고] ezdxf 미설치. pip install ezdxf")
        return _fallback_dxf_parse(path)

    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    groups: dict[str, list[dict]] = defaultdict(list)
    for e in msp:
        layer = getattr(e.dxf, "layer", "0") or "0"
        group = _classify_layer(layer)
        record = {
            "type": e.dxftype(),
            "layer": layer,
            "handle": e.dxf.handle,
        }
        if hasattr(e.dxf, "start"):
            record["start"] = list(e.dxf.start)
        if hasattr(e.dxf, "end"):
            record["end"] = list(e.dxf.end)
        if hasattr(e.dxf, "insert"):
            record["insert"] = list(e.dxf.insert)
        if hasattr(e.dxf, "name"):
            record["block_name"] = e.dxf.name
        groups[group].append(record)

    return dict(groups)


def _classify_layer(layer: str) -> str:
    for name, pattern in LAYER_GROUPS.items():
        if pattern and pattern.search(layer):
            return name
    return "기타"


def _fallback_dxf_parse(path: str) -> dict[str, list[dict]]:
    """ezdxf 없을 때 텍스트 파싱 폴백 (LINE/POLYLINE/INSERT 한정)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    current: dict[str, Any] = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        code = lines[i].strip()
        val = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if code == "0" and val in ("LINE", "POLYLINE", "INSERT", "LWPOLYLINE"):
            if current:
                layer = current.get("layer", "0")
                groups[_classify_layer(layer)].append(current)
            current = {"type": val}
        elif code == "8":
            current["layer"] = val
        elif code == "2" and current.get("type") == "INSERT":
            current["block_name"] = val
        i += 2

    if current:
        layer = current.get("layer", "0")
        groups[_classify_layer(layer)].append(current)

    return dict(groups)


def chunk_group(entities: list[dict], threshold: int = CHUNK_THRESHOLD) -> list[list[dict]]:
    """entity 수 초과 시 청크 분할 (단순 N등분 — 좌표 기반 고도화는 이천 결단 후)."""
    if len(entities) <= threshold:
        return [entities]
    n = (len(entities) + threshold - 1) // threshold
    return [entities[i * threshold:(i + 1) * threshold] for i in range(n)]


# ── LLM 호출 (ChainedProvider 연동 or HTTP 직접) ──────────────────────────────

def _make_prompt(group: str, entities: list[dict], pattern_seeds: str) -> str:
    sample = entities[:200]
    return f"""당신은 건설 구조도면(DXF) 분석 전문 AI입니다.

[패턴 라이브러리 시드 — {group} 관련]
{pattern_seeds}

[DXF 레이어 데이터 — {group}]
entity 수: {len(entities)}개 (샘플 200개 표시)
{json.dumps(sample, ensure_ascii=False, indent=2)[:8000]}

[출력 형식 — JSON만 출력, 설명 없음]
{{
  "matched_patterns": [{{"pattern_id": "A-1", "count": 0, "samples": []}}],
  "new_candidates": [{{"desc": "...", "evidence": []}}],
  "anomalies": [{{"entity": "...", "reason": "...", "surprise": 0.0}}],
  "stats": {{"total": {len(entities)}, "layer_group": "{group}"}}
}}"""


def _synthesis_prompt(results: list[dict], all_entities_count: int) -> str:
    return f"""당신은 건설 구조도면 분석 총괄 AI입니다.
아래 4개 분석 결과를 정반합하여 최종 보고서를 JSON으로 출력하세요.

총 entity 수: {all_entities_count}
4체 분석 결과:
{json.dumps(results, ensure_ascii=False, indent=2)[:12000]}

[출력 형식 — JSON만]
{{
  "final_patterns": [{{"pattern_id": "...", "confirmed": true, "count": 0}}],
  "new_pattern_candidates": [{{"desc": "...", "confidence": 0.0, "consensus": 0}}],
  "anomalies": [{{"entity": "...", "reason": "...", "surprise": 0.0}}],
  "summary": {{
    "total_entities": 0,
    "matched_count": 0,
    "new_candidates": 0,
    "anomaly_count": 0,
    "processing_note": "..."
  }}
}}"""


async def call_llm(provider: str, prompt: str, label: str) -> dict:
    """단일 LLM 비동기 호출. ChainedProvider 우선, 없으면 Groq HTTP."""
    t0 = time.time()
    try:
        from scripts.agent_nodes import call_llm_node
        response = await asyncio.get_event_loop().run_in_executor(
            None, call_llm_node, prompt, provider
        )
    except Exception:
        response = await _call_groq_http(prompt)

    elapsed = time.time() - t0
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        data = json.loads(response[start:end]) if start != -1 else {"raw": response[:500]}
    except Exception:
        data = {"raw": response[:500]}

    print(f"  [{label}] {elapsed:.1f}s — entities: {data.get('stats', {}).get('total', '?')}")
    return data


async def _call_groq_http(prompt: str) -> str:
    """Groq API 직접 HTTP 폴백."""
    import urllib.request
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return '{"error": "GROQ_API_KEY not set"}'
    payload = json.dumps({
        "model": "llama-3.1-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


# ── 5체 병렬 오케스트레이션 ───────────────────────────────────────────────────

async def five_phase_synthesis(groups: dict[str, list[dict]], pattern_seeds: str) -> dict:
    providers = {
        "기둥": "deepseek",
        "보_슬라브": "gemini",
        "벽체": "groq",
        "기타": "claude",
    }

    tasks = []
    labels = []
    for group, provider in providers.items():
        if "_" in group:
            parts = group.split("_")
            entities = []
            for p in parts:
                entities += groups.get(p, [])
        else:
            entities = groups.get(group, [])

        if not entities:
            continue

        for chunk_idx, chunk in enumerate(chunk_group(entities)):
            label = f"{group}체[{chunk_idx}]/{provider}"
            prompt = _make_prompt(group, chunk, pattern_seeds)
            tasks.append(call_llm(provider, prompt, label))
            labels.append(label)

    print(f"\n[피지수 5체] {len(tasks)}개 병렬 호출 시작...")
    phase1_results = await asyncio.gather(*tasks, return_exceptions=True)

    # 에러 필터
    valid = [r for r in phase1_results if isinstance(r, dict) and "error" not in r]
    print(f"[피지수 5체] {len(valid)}/{len(tasks)} 성공 → 정반합 진입")

    total_entities = sum(len(v) for v in groups.values())
    synthesis_prompt = _synthesis_prompt(valid, total_entities)
    final = await call_llm("deepseek", synthesis_prompt, "5체(정반합)")
    return final


# ── pattern_library 갱신 ──────────────────────────────────────────────────────

def update_pattern_library(result: dict, pattern_lib_path: Path) -> int:
    """신뢰도 ≥ 0.4인 신규 패턴을 pattern_library.md에 자동 추가."""
    candidates = result.get("new_pattern_candidates", [])
    if not candidates:
        return 0

    added = 0
    new_lines = [f"\n\n## 피지수 자동 갱신 — {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    for c in candidates:
        confidence = c.get("confidence", 0.0)
        if confidence >= 0.4:
            new_lines.append(
                f"- **[자동확정]** {c.get('desc', '?')} "
                f"(신뢰도={confidence:.2f}, 합의={c.get('consensus', 0)}/4)"
            )
            added += 1
        else:
            new_lines.append(
                f"- **[후보]** {c.get('desc', '?')} "
                f"(신뢰도={confidence:.2f} — 이천 수동 확인 필요)"
            )

    if new_lines:
        with open(pattern_lib_path, "a", encoding="utf-8") as f:
            f.write("\n".join(new_lines))

    return added


# ── 메인 ──────────────────────────────────────────────────────────────────────

async def main(dxf_path: str, pattern_lib: str | None) -> None:
    p = Path(dxf_path)
    if not p.exists():
        print(f"[오류] DXF 파일 없음: {dxf_path}")
        print("  이천 본진(Windows)에서 실행하거나 NAS 마운트 후 경로 지정 필요.")
        sys.exit(1)

    print(f"[피지수] DXF 로드: {p.name} ({p.stat().st_size / 1e6:.1f} MB)")
    t_start = time.time()

    groups = load_dxf(dxf_path)
    total = sum(len(v) for v in groups.values())
    print(f"[피지수] 레이어 분류 완료:")
    for g, ents in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"  {g}: {len(ents)}개 entity")
    print(f"  총계: {total}개 entity")

    pattern_seeds = ""
    if pattern_lib:
        pp = Path(pattern_lib)
        if pp.exists():
            pattern_seeds = pp.read_text(encoding="utf-8")[:3000]
            print(f"[피지수] pattern_library 로드: {len(pattern_seeds)}자")

    result = await five_phase_synthesis(groups, pattern_seeds)

    elapsed = time.time() - t_start
    print(f"\n[피지수] 완료 — {elapsed:.1f}초")

    out_path = ROOT / f"output_icheon_dxf_{p.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[피지수] 결과 저장: {out_path}")

    summary = result.get("summary", {})
    print(f"\n[정반합 요약]")
    print(f"  총 entity: {summary.get('total_entities', total)}")
    print(f"  매칭 패턴: {summary.get('matched_count', '?')}")
    print(f"  신규 후보: {summary.get('new_candidates', '?')}")
    print(f"  이상치:   {summary.get('anomaly_count', '?')}")

    if pattern_lib:
        pp = Path(pattern_lib)
        if pp.exists():
            added = update_pattern_library(result, pp)
            print(f"  pattern_library 자동 추가: {added}건")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local", override=True)

    ap = argparse.ArgumentParser(description="이천 大業 DXF 병렬처리 PoC")
    ap.add_argument("dxf", help="DXF 파일 경로")
    ap.add_argument(
        "--pattern-lib",
        default=None,
        help="pattern_library.md 경로 (ex: D:/Git/FreeCAD_4TH/.brain/pattern_library.md)",
    )
    args = ap.parse_args()
    asyncio.run(main(args.dxf, args.pattern_lib))
