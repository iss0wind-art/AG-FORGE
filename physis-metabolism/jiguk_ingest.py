"""
피지수의 *보편 흡수* — 7사 brain·CLAUDE를 도메인별 ChromaDB 컬렉션에 박제.

청사진 A 2층. 정독(jiguk_read)이 *읽기*라면 ingest는 *흡수* — 피지수의 직관층에 영속 박제.

도메인별 컬렉션:
  - physis_jiguk_governance      (본영·BOQQQ pending)
  - physis_jiguk_finance         (4지국 STOCK)
  - physis_jiguk_construction    (1지국 BOQ)
  - physis_jiguk_operations      (2지국 H2OWIND)
  - physis_jiguk_design          (3지국 FreeCAD)

사용:
  python jiguk_ingest.py --all                      # 7사 전체 흡수
  python jiguk_ingest.py --jiguk 1_boq               # 1지국만
  python jiguk_ingest.py --domain finance            # 도메인별
  python jiguk_ingest.py --query "BOQ 단가 정밀도" --domain construction
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import chromadb

REGISTRY = Path("/home/nas/AG-Forge/physis-metabolism/jiguk_registry.yaml")
CHROMA_PATH = "/home/nas/AG-Forge/physis_memory/.chromadb"
CHUNK_SIZE = 1500           # 한 chunk 1500자 (의미 단위 유지)
CHUNK_OVERLAP = 150


def load_registry() -> dict:
    import yaml
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + chunk_size])
        i += chunk_size - overlap
    return chunks


def read_file_for_ingest(fp: Path) -> str:
    try:
        if not fp.exists():
            return ""
        if fp.is_dir():
            content = []
            for sub in sorted(fp.glob("**/*.md"))[:30]:
                try:
                    content.append(f"\n\n=== {sub.name} ===\n" + sub.read_text(encoding="utf-8"))
                except Exception:
                    continue
            return "".join(content)
        return fp.read_text(encoding="utf-8")
    except Exception:
        return ""


def get_collection(client, domain: str, reg: dict):
    coll_name = reg["domain_collections"].get(domain, f"physis_jiguk_{domain}")
    return client.get_or_create_collection(coll_name, metadata={"domain": domain})


def ingest_jiguk(client, j: dict, reg: dict) -> dict:
    coll = get_collection(client, j["domain"], reg)
    existing = set()
    try:
        existing = set(coll.get(include=[]).get("ids", []))
    except Exception:
        pass

    new_docs, new_ids, new_metas = [], [], []
    skipped = 0

    for bf in j.get("brain_files", []):
        fp = Path(bf)
        text = read_file_for_ingest(fp)
        if not text:
            continue
        chunks = chunk_text(text)
        for idx, ch in enumerate(chunks):
            cid = f"{j['id']}::{fp.name}::chunk{idx}"
            if cid in existing:
                skipped += 1
                continue
            new_ids.append(cid)
            new_docs.append(ch)
            new_metas.append({
                "jiguk_id": j["id"],
                "jiguk_name": j["name"],
                "source_file": str(fp),
                "domain": j["domain"],
                "tier": j["tier"],
                "chunk_idx": idx,
                "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })

    # 4지국은 code_roots도 인제스트 (외부 라이브러리·캐시 제외)
    EXCLUDE_PARTS = {".venv", "venv", "__pycache__", "node_modules", ".git",
                     "site-packages", "dist", "build", ".pytest_cache"}
    for cr in j.get("code_roots", []):
        cr_path = Path(cr)
        if not cr_path.exists():
            continue
        # .py 파일만 (코드 인제스트), 외부 라이브러리 제외
        candidates = []
        for pf in cr_path.rglob("*.py"):
            if any(part in EXCLUDE_PARTS for part in pf.parts):
                continue
            candidates.append(pf)
        candidates.sort()
        for pf in candidates[:40]:  # 한도 20 → 40 (자체 코드는 더 흡수)
            try:
                text = pf.read_text(encoding="utf-8")
            except Exception:
                continue
            if not text or len(text) < 100:
                continue
            chunks = chunk_text(text)
            # 파일 path의 상대 경로 hash로 unique ID (같은 이름 파일 충돌 회피)
            try:
                rel = pf.relative_to(cr_path)
                path_tag = str(rel).replace("/", "_").replace("\\", "_")
            except Exception:
                path_tag = pf.name
            for idx, ch in enumerate(chunks[:5]):  # py당 최대 5 chunk
                cid = f"{j['id']}::{path_tag}::chunk{idx}"
                if cid in existing:
                    skipped += 1
                    continue
                new_ids.append(cid)
                new_docs.append(ch)
                new_metas.append({
                    "jiguk_id": j["id"],
                    "jiguk_name": j["name"],
                    "source_file": str(pf),
                    "domain": j["domain"],
                    "tier": j["tier"],
                    "chunk_idx": idx,
                    "file_type": "code",
                    "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                })

    if new_docs:
        BATCH = 50
        for i in range(0, len(new_docs), BATCH):
            coll.add(documents=new_docs[i:i+BATCH], ids=new_ids[i:i+BATCH], metadatas=new_metas[i:i+BATCH])

    return {
        "jiguk": j["id"],
        "domain": j["domain"],
        "collection": coll.name,
        "ingested_new": len(new_docs),
        "skipped_existing": skipped,
        "collection_total": coll.count(),
    }


def cmd_all(reg: dict) -> int:
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    results = []
    for j in reg["jiguk"]:
        r = ingest_jiguk(client, j, reg)
        results.append(r)
        print(f"  [{r['jiguk']}] {r['domain']:25s} → +{r['ingested_new']} (총 {r['collection_total']}, skip {r['skipped_existing']})")
    print()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def cmd_jiguk(reg: dict, jid: str) -> int:
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    j = next((x for x in reg["jiguk"] if x["id"] == jid), None)
    if not j:
        print(f"지국 '{jid}' 없음", file=sys.stderr)
        return 2
    r = ingest_jiguk(client, j, reg)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


def cmd_domain(reg: dict, domain: str) -> int:
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    matches = [j for j in reg["jiguk"] if j["domain"] == domain]
    for j in matches:
        r = ingest_jiguk(client, j, reg)
        print(f"  [{r['jiguk']}] → +{r['ingested_new']} (총 {r['collection_total']})")
    return 0


def cmd_query(reg: dict, query: str, domain: str | None, top_k: int) -> int:
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    if domain:
        coll = get_collection(client, domain, reg)
        if coll.count() == 0:
            print(f"컬렉션 비어있음. --domain {domain} ingest 먼저")
            return 2
        res = coll.query(query_texts=[query], n_results=min(top_k, coll.count()))
        print(f"질의: \"{query}\"  domain={domain}  컬렉션={coll.name} ({coll.count()}건)")
        print("-" * 70)
        for i in range(len(res["documents"][0])):
            doc = res["documents"][0][i]
            meta = res["metadatas"][0][i]
            dist = res["distances"][0][i] if res.get("distances") else None
            print(f"[{i+1}] dist={dist:.3f}  {meta.get('jiguk_id','?')} :: {Path(meta.get('source_file','?')).name}")
            print(f"    {doc[:200]}")
            print()
    else:
        # 전 도메인 검색
        for dom_name, coll_name in reg["domain_collections"].items():
            try:
                coll = client.get_collection(coll_name)
                if coll.count() == 0:
                    continue
                res = coll.query(query_texts=[query], n_results=min(2, coll.count()))
                print(f"\n=== {dom_name} ({coll_name}, {coll.count()}건) ===")
                for i in range(len(res["documents"][0])):
                    doc = res["documents"][0][i]
                    meta = res["metadatas"][0][i]
                    dist = res["distances"][0][i] if res.get("distances") else None
                    print(f"  [{i+1}] dist={dist:.3f}  {meta.get('jiguk_id','?')} :: {Path(meta.get('source_file','?')).name}")
                    print(f"      {doc[:160]}")
            except Exception:
                continue
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--jiguk", type=str, default=None)
    ap.add_argument("--domain", type=str, default=None)
    ap.add_argument("--query", type=str, default=None)
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()
    reg = load_registry()
    if args.query:
        return cmd_query(reg, args.query, args.domain, args.top_k)
    if args.all:
        return cmd_all(reg)
    if args.jiguk:
        return cmd_jiguk(reg, args.jiguk)
    if args.domain:
        return cmd_domain(reg, args.domain)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
