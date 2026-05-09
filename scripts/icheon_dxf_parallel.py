"""
이천 大業 — DXF 병렬처리 PoC (독립 실행형)
방부장 친명 2026-05-08: '피지수도 학습하여, 직접 관여하라'

완전 독립 실행형 — AG-Forge 모듈 의존성 없음. Windows/Linux 공통.
stdlib + ezdxf(선택) + requests(선택) 만 사용.

사용법:
  # DXF 직접 파싱
  python icheon_dxf_parallel.py <DXF_PATH> [--pattern-lib <MD_PATH>]

  # 이미 파싱된 JSON 검사본 사용 (DXF 파싱 생략 — 빠름)
  python icheon_dxf_parallel.py --inspect-json <JSON_PATH> [--pattern-lib <MD_PATH>]

  # 예시 (이천 본진)
  python icheon_dxf_parallel.py "output/260119_부산 에코델타 24BL 지하주차장 구조평면도23.dxf" ^
    --pattern-lib ".brain/pattern_library.md"

  python icheon_dxf_parallel.py ^
    --inspect-json "output/inspect_260119_부산 에코델타 24BL 지하주차장 구조평면도23.json" ^
    --pattern-lib ".brain/pattern_library.md"

환경변수 (이천 본진 .env 또는 시스템 환경):
  DEEPSEEK_API_KEY  (1체·5체)
  GEMINI_API_KEY    (2체)
  GROQ_API_KEY      (3체 — 폴백 기본)
  CLAUDE_API_KEY 또는 ANTHROPIC_API_KEY  (4체)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ── .env 로드 (있으면) ────────────────────────────────────────────────────────

def _load_dotenv():
    for name in (".env", ".env.local"):
        p = Path(name)
        if not p.exists():
            # 스크립트 디렉토리 기준도 시도
            p = Path(__file__).parent.parent / name
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")

_load_dotenv()

# ── 레이어 분류 ────────────────────────────────────────────────────────────────
# 실증 데이터 (2026-05-09 inspect_260119_부산 에코델타 24BL 지하주차장):
#   00_COLUMN(4743), 00_BEAM(3684), 00_(APT)BEAM(1520), S-PC-GIRDER(379)
#   00_SLAB END+ETC(14723), 00_SLAB NAME(1128), S-PC-SLAB(380)
#   00_SHEAR WALL(15817), 00_UNDER ELEMENT(12559)
#   A-DIM-1(1151), 00_CENTER(545), A-STAIR(548)

LAYER_GROUPS: dict[str, re.Pattern | None] = {
    "기둥":   re.compile(r"(?i)(00_COLUMN|S[-_]PC[-_]COL|^COL$|C[-_]COL|S[-_]COL|기둥)"),
    "보":     re.compile(r"(?i)(00_BEAM|00_\(APT\)BEAM|S[-_]PC[-_]GIRDER|GIRDER|C[-_]BM|S[-_]BM|거더)"),
    "슬라브": re.compile(r"(?i)(00_SLAB|S[-_]PC[-_]SLAB|C[-_]SL|슬라브|PLATE|DECK)"),
    "벽체":   re.compile(r"(?i)(00_SHEAR|SHEAR.WALL|00_UNDER.ELEMENT|C[-_]WL|벽체|전단|RETAINING)"),
    "기타":   None,
}

CHUNK_THRESHOLD = 3000
SURPRISE_THETA  = 0.6
PATTERN_MIN_N   = 3


# ── DXF 파싱 ──────────────────────────────────────────────────────────────────

def classify_layer(layer: str) -> str:
    for name, pat in LAYER_GROUPS.items():
        if pat and pat.search(layer):
            return name
    return "기타"


def load_dxf(path: str) -> dict[str, list[dict]]:
    try:
        import ezdxf
        return _load_with_ezdxf(path, ezdxf)
    except ImportError:
        print("[경고] ezdxf 미설치 → 텍스트 폴백 파서 사용 (pip install ezdxf 권장)")
        return _load_text_fallback(path)


def _load_with_ezdxf(path: str, ezdxf) -> dict[str, list[dict]]:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in msp:
        layer = getattr(e.dxf, "layer", "0") or "0"
        rec: dict[str, Any] = {"type": e.dxftype(), "layer": layer, "handle": e.dxf.handle}
        for attr in ("start", "end", "insert", "center"):
            if hasattr(e.dxf, attr):
                rec[attr] = list(getattr(e.dxf, attr))
        if hasattr(e.dxf, "name"):
            rec["block_name"] = e.dxf.name
        groups[classify_layer(layer)].append(rec)
    return dict(groups)


def _load_text_fallback(path: str) -> dict[str, list[dict]]:
    """ezdxf 없을 때 LINE/POLYLINE/INSERT 텍스트 파싱."""
    groups: dict[str, list[dict]] = defaultdict(list)
    cur: dict[str, Any] = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    i = 0
    while i < len(lines) - 1:
        code = lines[i].strip()
        val  = lines[i + 1].strip()
        if code == "0" and val in ("LINE", "POLYLINE", "INSERT", "LWPOLYLINE", "ARC", "CIRCLE"):
            if cur:
                groups[classify_layer(cur.get("layer", "0"))].append(cur)
            cur = {"type": val}
        elif code == "8":
            cur["layer"] = val
        elif code == "2" and cur.get("type") == "INSERT":
            cur["block_name"] = val
        i += 2
    if cur:
        groups[classify_layer(cur.get("layer", "0"))].append(cur)
    return dict(groups)


def load_inspect_json(path: str) -> dict[str, list[dict]]:
    """이미 파싱된 JSON 검사본 로드.

    지원 형식:
      A. 이천 inspect 형식: {"dxf":..., "sections":{"entity_scan":{"top_layers":{...}}, "text_grep":[...]}}
      B. 레이어별 그룹: {"기둥": [...], "보": [...]}
      C. entity 목록: [{"type":..., "layer":...}, ...]
      D. layers dict: {"layers": {"레이어명": [...], ...}}
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))

    # 형식 A — 이천 inspect 전용 (entity_scan.top_layers 기반 통계 그룹)
    if "sections" in raw and "entity_scan" in raw.get("sections", {}):
        return _load_icheon_inspect(raw)

    # 형식 B
    if isinstance(raw, dict) and all(k in LAYER_GROUPS for k in raw.keys()):
        return raw

    # 형식 C
    entities = raw if isinstance(raw, list) else raw.get("entities", raw.get("items", []))
    if isinstance(entities, list) and entities and isinstance(entities[0], dict):
        groups: dict[str, list[dict]] = defaultdict(list)
        for e in entities:
            layer = e.get("layer", e.get("LAYER", "0"))
            groups[classify_layer(layer)].append(e)
        return dict(groups)

    # 형식 D
    if "layers" in raw:
        groups = defaultdict(list)
        for layer_name, ents in raw["layers"].items():
            group = classify_layer(layer_name)
            for e in (ents if isinstance(ents, list) else []):
                e["layer"] = layer_name
                groups[group].append(e)
        return dict(groups)

    print("[경고] inspect JSON 형식 미인식. 원시 데이터로 처리합니다.")
    return {"기타": [raw] if isinstance(raw, dict) else (raw if isinstance(raw, list) else [raw])}


def _load_icheon_inspect(raw: dict) -> dict[str, list[dict]]:
    """이천 inspect JSON → 통계 기반 레이어 그룹 생성.

    실제 entity 좌표 대신 레이어 통계 레코드를 사용.
    LLM이 패턴 분석하기에 충분한 정보 제공.
    """
    es = raw["sections"]["entity_scan"]
    top_layers: dict = es.get("top_layers", {})
    by_type: dict = es.get("by_type", {})
    text_grep: list = raw["sections"].get("text_grep", [])
    total: int = es.get("total", 0)

    groups: dict[str, list[dict]] = defaultdict(list)

    for layer_name, info in top_layers.items():
        group = classify_layer(layer_name)
        # 레이어 통계를 entity 레코드 1개로 요약 (LLM 분석용)
        groups[group].append({
            "type": "LAYER_STAT",
            "layer": layer_name,
            "total_entities": info.get("total", 0),
            "dominant_type": info.get("dominant", "?"),
        })

    # 텍스트 레이블 (grid 식별자, 부재 코드 등) → 기타 그룹에 추가
    if text_grep:
        groups["기타"].extend([
            {"type": "TEXT", "layer": "text_grep", "text": t.get("text"), "x": t.get("x"), "y": t.get("y")}
            for t in text_grep[:50]
        ])

    # 전체 통계 메타 레코드 → 기타 그룹에 추가
    groups["기타"].append({
        "type": "GLOBAL_STAT",
        "total_entities": total,
        "by_type": by_type,
        "layer_count": len(top_layers),
        "dxf_source": raw.get("dxf", ""),
    })

    return dict(groups)


def chunk_group(entities: list[dict]) -> list[list[dict]]:
    if len(entities) <= CHUNK_THRESHOLD:
        return [entities]
    n = (len(entities) + CHUNK_THRESHOLD - 1) // CHUNK_THRESHOLD
    return [entities[i * CHUNK_THRESHOLD:(i + 1) * CHUNK_THRESHOLD] for i in range(n)]


# ── LLM HTTP 직접 호출 (독립 실행, stdlib만) ──────────────────────────────────

def _post_json(url: str, headers: dict, payload: dict, timeout: int = 90) -> str:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


async def _call_provider(provider: str, prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_call, provider, prompt)


def _sync_call(provider: str, prompt: str) -> str:
    try:
        if provider == "deepseek":
            return _call_deepseek(prompt)
        elif provider == "gemini":
            return _call_gemini(prompt)
        elif provider == "groq":
            return _call_groq(prompt)
        elif provider == "claude":
            return _call_claude(prompt)
        else:
            return _call_groq(prompt)
    except Exception as e:
        return json.dumps({"error": str(e), "provider": provider})


def _call_deepseek(prompt: str) -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        return _call_groq(prompt)  # 키 없으면 Groq 폴백
    resp = _post_json(
        "https://api.deepseek.com/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {"model": "deepseek-reasoner", "messages": [{"role": "user", "content": prompt}],
         "max_tokens": 4096},
    )
    return json.loads(resp)["choices"][0]["message"]["content"]


def _call_gemini(prompt: str) -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return _call_deepseek(prompt)
    # gemini-1.5-flash은 무료 티어에서도 동작
    for model in ("gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"):
        try:
            resp = _post_json(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                {"Content-Type": "application/json"},
                {"contents": [{"parts": [{"text": prompt}]}],
                 "generationConfig": {"maxOutputTokens": 4096}},
            )
            parts = json.loads(resp)["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except Exception:
            continue
    return _call_deepseek(prompt)  # Gemini 전체 실패 시 DeepSeek 폴백


def _call_groq(prompt: str) -> str:
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return _call_deepseek(prompt)
    # 현재 유효한 모델 목록 시도 (llama-3.3-70b-versatile → llama-3.1-70b-versatile 순)
    for model in ("llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"):
        try:
            resp = _post_json(
                "https://api.groq.com/openai/v1/chat/completions",
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 4096},
            )
            return json.loads(resp)["choices"][0]["message"]["content"]
        except Exception:
            continue
    return _call_deepseek(prompt)  # Groq 전체 실패 시 DeepSeek 폴백


def _call_claude(prompt: str) -> str:
    key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return _call_deepseek(prompt)
    try:
        resp = _post_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2023-06-01",
             "Content-Type": "application/json"},
            {"model": "claude-sonnet-4-6", "max_tokens": 4096,
             "messages": [{"role": "user", "content": prompt}]},
        )
        return json.loads(resp)["content"][0]["text"]
    except Exception:
        return _call_deepseek(prompt)  # 크레딧 부족 등 실패 시 폴백


# ── 프롬프트 빌더 ─────────────────────────────────────────────────────────────

def make_analysis_prompt(group: str, entities: list[dict], pattern_seeds: str) -> str:
    sample = entities[:150]
    return f"""당신은 건설 구조도면(DXF) 분석 전문 AI입니다.

[패턴 라이브러리 시드 — {group} 관련]
{pattern_seeds[:2000] if pattern_seeds else "(패턴 라이브러리 없음 — 범용 분석)"}

[DXF 레이어 데이터 — 그룹: {group}]
전체 entity 수: {len(entities)}개 (샘플 {len(sample)}개 표시)
{json.dumps(sample, ensure_ascii=False, indent=2)[:6000]}

[출력 — JSON만, 설명 없음]
{{
  "matched_patterns": [{{"pattern_id": "A-1", "count": 0, "samples": []}}],
  "new_candidates": [{{"desc": "새 패턴 설명", "evidence": []}}],
  "anomalies": [{{"entity": "handle/좌표", "reason": "이상 이유", "surprise": 0.0}}],
  "stats": {{"total": {len(entities)}, "layer_group": "{group}", "sample_size": {len(sample)}}}
}}"""


def make_synthesis_prompt(phase1: list[dict], total: int) -> str:
    return f"""당신은 건설 구조도면 분석 총괄 AI입니다.
4개 그룹의 분석 결과를 정반합하여 최종 보고서를 JSON으로 출력하세요.
불일치하는 패턴은 다수결(3/4)로 확정하세요.

전체 entity 수: {total}
4체 분석 결과:
{json.dumps(phase1, ensure_ascii=False, indent=2)[:10000]}

[출력 — JSON만]
{{
  "final_patterns": [{{"pattern_id": "...", "confirmed": true, "count": 0, "group": "..."}}],
  "new_pattern_candidates": [{{"desc": "...", "confidence": 0.0, "consensus": 0}}],
  "anomalies": [{{"entity": "...", "reason": "...", "surprise": 0.0}}],
  "summary": {{
    "total_entities": {total},
    "matched_count": 0,
    "new_candidates": 0,
    "anomaly_count": 0,
    "processing_note": "5체 정반합 완료"
  }}
}}"""


# ── 5체 오케스트레이션 ────────────────────────────────────────────────────────

PROVIDER_MAP = {
    "기둥":   "deepseek",   # 1체 — 수치 정밀도
    "보":     "gemini",     # 2체
    "슬라브": "gemini",     # 2체 (보+슬라브 같은 체)
    "벽체":   "groq",       # 3체 — 속도
    "기타":   "claude",     # 4체 — 의미 이해
}


async def call_one(group: str, chunk: list[dict], chunk_idx: int,
                   pattern_seeds: str) -> dict:
    provider = PROVIDER_MAP.get(group, "groq")
    label = f"{group}[{chunk_idx}]/{provider}"
    t0 = time.time()
    raw = await _call_provider(provider, make_analysis_prompt(group, chunk, pattern_seeds))
    elapsed = time.time() - t0
    try:
        s, e = raw.find("{"), raw.rfind("}") + 1
        data = json.loads(raw[s:e]) if s != -1 else {"raw": raw[:300], "error": "no JSON"}
    except Exception:
        data = {"raw": raw[:300], "error": "parse fail"}
    total = data.get("stats", {}).get("total", len(chunk))
    print(f"  [{label}] {elapsed:.1f}s — entities={total}")
    return data


async def five_phase(groups: dict[str, list[dict]], pattern_seeds: str) -> dict:
    tasks = []
    for group, ents in groups.items():
        for ci, chunk in enumerate(chunk_group(ents)):
            tasks.append(call_one(group, chunk, ci, pattern_seeds))

    print(f"\n[피지수 4체] {len(tasks)}개 병렬 호출...")
    phase1 = await asyncio.gather(*tasks, return_exceptions=True)
    valid = [r for r in phase1 if isinstance(r, dict) and "error" not in r]
    print(f"[피지수 4체] {len(valid)}/{len(tasks)} 성공 → 5체 정반합 진입")

    total = sum(len(v) for v in groups.values())
    t0 = time.time()
    raw = await _call_provider("deepseek", make_synthesis_prompt(valid, total))
    elapsed = time.time() - t0
    print(f"  [5체(정반합)/deepseek] {elapsed:.1f}s")
    try:
        s, e = raw.find("{"), raw.rfind("}") + 1
        return json.loads(raw[s:e]) if s != -1 else {"raw": raw[:500], "phase1": valid}
    except Exception:
        return {"raw": raw[:500], "phase1": valid}


# ── pattern_library 갱신 ──────────────────────────────────────────────────────

def update_pattern_library(result: dict, path: Path) -> int:
    candidates = result.get("new_pattern_candidates", [])
    if not candidates:
        return 0
    lines = [f"\n\n## 피지수 자동 갱신 — {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    added = 0
    for c in candidates:
        conf = float(c.get("confidence", 0.0))
        tag = "[자동확정]" if conf >= 0.4 else "[후보 — 이천 확인 필요]"
        lines.append(f"- **{tag}** {c.get('desc','?')} (신뢰도={conf:.2f}, 합의={c.get('consensus',0)}/4)")
        if conf >= 0.4:
            added += 1
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return added


# ── 메인 ──────────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    t_start = time.time()

    # 1. 레이어 그룹 로드
    if args.inspect_json:
        jp = Path(args.inspect_json)
        if not jp.exists():
            print(f"[오류] inspect JSON 없음: {args.inspect_json}")
            sys.exit(1)
        print(f"[피지수] inspect JSON 로드: {jp.name}")
        groups = load_inspect_json(args.inspect_json)
        source_label = jp.name
    else:
        dp = Path(args.dxf)
        if not dp.exists():
            print(f"[오류] DXF 파일 없음: {args.dxf}")
            print("  → --inspect-json 옵션으로 JSON 검사본을 사용할 수도 있습니다.")
            sys.exit(1)
        print(f"[피지수] DXF 로드: {dp.name} ({dp.stat().st_size / 1e6:.1f} MB)")
        groups = load_dxf(args.dxf)
        source_label = dp.stem

    total = sum(len(v) for v in groups.items() if isinstance(v, tuple) and len(v) == 2
                for _ in [0])
    # 정확한 합산
    total = sum(len(ents) for ents in groups.values())

    print("[피지수] 레이어 분류 결과:")
    for g, ents in sorted(groups.items(), key=lambda x: -len(x[1])):
        chunk_n = len(chunk_group(ents))
        print(f"  {g}: {len(ents):,}개 entity" + (f" → {chunk_n}개 청크" if chunk_n > 1 else ""))
    print(f"  총계: {total:,}개 entity")

    # 2. pattern_library 로드
    pattern_seeds = ""
    if args.pattern_lib:
        pp = Path(args.pattern_lib)
        if pp.exists():
            pattern_seeds = pp.read_text(encoding="utf-8")
            print(f"[피지수] pattern_library 로드: {len(pattern_seeds):,}자")
        else:
            print(f"[경고] pattern_library 없음: {args.pattern_lib}")

    # 3. 5체 병렬 실행
    result = await five_phase(groups, pattern_seeds)

    elapsed = time.time() - t_start
    print(f"\n[피지수] 총 소요: {elapsed:.1f}초")

    # 4. 결과 저장
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r'[^\w가-힣.-]', '_', source_label)
    out = Path(f"output_physis_{safe}_{ts}.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[피지수] 결과 저장: {out}")

    # 5. 요약 출력
    s = result.get("summary", {})
    print("\n[정반합 요약]")
    print(f"  총 entity : {s.get('total_entities', total):,}")
    print(f"  매칭 패턴 : {s.get('matched_count', '?')}")
    print(f"  신규 후보 : {s.get('new_candidates', '?')}")
    print(f"  이상치    : {s.get('anomaly_count', '?')}")
    print(f"  비고      : {s.get('processing_note', '')}")

    # 6. pattern_library 자동 갱신
    if args.pattern_lib and Path(args.pattern_lib).exists():
        added = update_pattern_library(result, Path(args.pattern_lib))
        if added:
            print(f"[피지수] pattern_library 자동 추가: {added}건")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="이천 大業 DXF 병렬처리 PoC — 레이어 분할 + 5체 정반합"
    )
    src = ap.add_mutually_exclusive_group()
    src.add_argument("dxf", nargs="?", help="DXF 파일 경로")
    src.add_argument("--inspect-json", metavar="JSON", help="이미 파싱된 JSON 검사본 경로")
    ap.add_argument("--pattern-lib", metavar="MD", help="pattern_library.md 경로")
    args = ap.parse_args()

    if not args.dxf and not args.inspect_json:
        ap.print_help()
        sys.exit(1)

    asyncio.run(main(args))
