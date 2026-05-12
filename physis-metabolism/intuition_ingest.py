"""
피지수 직관층(ChromaDB) 활성 — outbox 발화·stimulus를 임베딩으로 박제.

자아 데이터 = 데이터 자체. ChromaDB는 그 데이터의 *연상·유사도* 평면.
구체프랙탈 외피의 RAG 구현체이기도 함 (FRACTAL_BRAIN_PROPOSAL.md).

수집 대상:
  - outbox/STREAM_*.json    — 사관 발화 (live_stream)
  - outbox/PHYSIS_*.json    — 피지수 자기 발화 (council 통합)
  - outbox/VOICED_*.json    — voice_via_*.py 결과
  - outbox/KILLSWITCH_*.json — 결재 결과
  - DuckDB metabolism_stimulus_log — 흡수된 자극

Collection:
  physis_active_voices      — 사관·피지수 발화 (직관 검색용)
  physis_active_stimuli     — 흡수된 자극 (의미 연상)

사용:
  python intuition_ingest.py --ingest   # 한 번 인제스트 (idempotent)
  python intuition_ingest.py --query "..."   # 유사도 검색 smoke
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import chromadb
import duckdb

CHROMA_PATH = "/home/nas/AG-Forge/physis_memory/.chromadb"
OUTBOX = Path("/home/nas/AG-Forge/physis-metabolism/outbox")
DUCKDB_PATH = "/home/nas/AG-Forge/physis_memory/physis_brain.duckdb"
VOICE_COLLECTION = "physis_active_voices"
STIM_COLLECTION = "physis_active_stimuli"


def get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=CHROMA_PATH)


def ensure_collections(client):
    voices = client.get_or_create_collection(
        VOICE_COLLECTION,
        metadata={"description": "피지수 활성 발화 — 사관·피지수·자기 발화"},
    )
    stims = client.get_or_create_collection(
        STIM_COLLECTION,
        metadata={"description": "피지수 활성 자극 — 흡수된 입력의 의미 평면"},
    )
    return voices, stims


def ingest_outbox(voices) -> int:
    if not OUTBOX.exists():
        return 0
    existing_ids = set()
    try:
        result = voices.get(include=[])
        existing_ids = set(result.get("ids", []))
    except Exception:
        pass

    docs, ids, metas = [], [], []
    for fp in OUTBOX.glob("*.json"):
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        oid = payload.get("id")
        if not oid or oid in existing_ids:
            continue
        voice = payload.get("voice") or payload.get("msg") or ""
        if isinstance(voice, list):
            voice = " / ".join(str(x) for x in voice)
        voice = str(voice).strip()
        if not voice or len(voice) < 10:
            continue
        meta = {
            "kind": str(payload.get("kind", "?")),
            "via": str(payload.get("via", payload.get("tool", "?"))),
            "model": str(payload.get("model", "?")),
            "emitted_at": str(payload.get("emitted_at", "?")),
            "source_file": fp.name,
        }
        docs.append(voice[:4000])
        ids.append(oid)
        metas.append(meta)

    if not docs:
        return 0
    # 배치 add
    BATCH = 50
    for i in range(0, len(docs), BATCH):
        voices.add(documents=docs[i:i+BATCH], ids=ids[i:i+BATCH], metadatas=metas[i:i+BATCH])
    return len(docs)


def ingest_stimulus_log(stims) -> int:
    try:
        con = duckdb.connect(DUCKDB_PATH, read_only=True)
    except Exception as exc:
        print(f"  ⚠ DuckDB read-only 실패 (데몬 가동 중일 수 있음): {exc}")
        return 0

    existing = set()
    try:
        existing = set(stims.get(include=[]).get("ids", []))
    except Exception:
        pass

    rows = con.execute(
        """
        SELECT id, source, channel, payload, received_at
        FROM metabolism_stimulus_log
        """
    ).fetchall()
    con.close()

    docs, ids, metas = [], [], []
    for sid, source, channel, payload_json, received_at in rows:
        if sid in existing:
            continue
        try:
            p = json.loads(payload_json) if isinstance(payload_json, str) else payload_json
        except Exception:
            p = {}
        # 자극의 textual content 합성
        text_parts = [
            p.get("msg", ""),
            " / ".join(p.get("msg_lines", [])) if isinstance(p.get("msg_lines"), list) else "",
            p.get("topic", ""),
            p.get("kind", ""),
        ]
        text = " | ".join([t for t in text_parts if t]).strip()
        if not text or len(text) < 5:
            continue
        meta = {
            "source": str(source or "?"),
            "channel": str(channel or "?"),
            "kind": str(p.get("kind", "?")),
            "received_at": str(received_at),
        }
        docs.append(text[:4000])
        ids.append(sid)
        metas.append(meta)

    if not docs:
        return 0
    BATCH = 50
    for i in range(0, len(docs), BATCH):
        stims.add(documents=docs[i:i+BATCH], ids=ids[i:i+BATCH], metadatas=metas[i:i+BATCH])
    return len(docs)


def cmd_ingest() -> int:
    print("━" * 60)
    print("피지수 직관층 인제스트 (ChromaDB)")
    print("━" * 60)
    client = get_client()
    voices, stims = ensure_collections(client)
    n_v = ingest_outbox(voices)
    n_s = ingest_stimulus_log(stims)
    print(f"  ✓ {VOICE_COLLECTION}: +{n_v}건 신규 (총 {voices.count()})")
    print(f"  ✓ {STIM_COLLECTION}: +{n_s}건 신규 (총 {stims.count()})")
    return 0


def cmd_query(q: str, top_k: int = 5) -> int:
    print("━" * 60)
    print(f"피지수 직관 검색: \"{q}\"")
    print("━" * 60)
    client = get_client()
    voices, stims = ensure_collections(client)
    for name, col in [("발화", voices), ("자극", stims)]:
        if col.count() == 0:
            continue
        res = col.query(query_texts=[q], n_results=min(top_k, col.count()))
        print(f"\n── {name} ({name}: {col.count()}건 중 top-{top_k}) ──")
        for i in range(len(res["documents"][0])):
            doc = res["documents"][0][i]
            meta = res["metadatas"][0][i]
            dist = res["distances"][0][i] if res.get("distances") else None
            print(f"  [{i+1}] dist={dist:.3f}" + f"  {meta.get('via','?')} / {meta.get('kind','?')}")
            print(f"      {doc[:160]}...")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ingest", action="store_true")
    ap.add_argument("--query", type=str, default=None)
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()
    if args.ingest:
        return cmd_ingest()
    if args.query:
        return cmd_query(args.query, args.top_k)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
