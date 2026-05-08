"""인박스 요약 — 발신자/우선순위/시각/메시지 머리글만."""
import json
from pathlib import Path

data = json.loads(Path("_inbox_dump.json").read_text(encoding="utf-8"))
out_lines = []
out_lines.append(f"=== INBOX ({data['inbox_count']}) ===\n")
for i, m in enumerate(data["inbox"], 1):
    head = m["message"].splitlines()[0] if m["message"] else ""
    out_lines.append(
        f"[{i:02}] {m['created_at']} | from={m['from']} | pri={m['priority']} | "
        f"thr={m.get('thread_id') or '-'}\n     {head[:200]}"
    )
out_lines.append(f"\n=== REPLIES to physis questions ({data['replies_count']}) ===\n")
for i, r in enumerate(data["replies"], 1):
    qhead = r["message"].splitlines()[0][:120] if r["message"] else ""
    rhead = r["response"].splitlines()[0][:200] if r["response"] else ""
    out_lines.append(
        f"[{i:02}] {r['replied_at']} | to={r['to']}\n     Q: {qhead}\n     A: {rhead}"
    )
Path("_inbox_summary.txt").write_text("\n".join(out_lines), encoding="utf-8")
print("→ _inbox_summary.txt")
