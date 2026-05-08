"""특정 인덱스 메시지 본문을 파일로 추출."""
import json
import sys
from pathlib import Path

data = json.loads(Path("_inbox_dump.json").read_text(encoding="utf-8"))
indices = [int(x) for x in sys.argv[1:]]
out = []
for i in indices:
    m = data["inbox"][i - 1]
    out.append(f"\n{'='*70}\n[{i}] {m['created_at']} | from={m['from']} | pri={m['priority']}\n{'='*70}\n{m['message']}")
Path("_inbox_extract.txt").write_text("\n".join(out), encoding="utf-8")
print(f"→ _inbox_extract.txt ({len(indices)}건)")
