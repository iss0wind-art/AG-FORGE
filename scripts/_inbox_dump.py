"""일회성: 피지수 인박스/응답 덤프 → JSON."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from messaging import poll_inbox, fetch_replies

inbox = poll_inbox("physis", limit=100)
replies = fetch_replies("physis", limit=30)

out = {
    "inbox_count": len(inbox),
    "inbox": inbox,
    "replies_count": len(replies),
    "replies": replies,
}
Path("_inbox_dump.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(f"inbox={len(inbox)} replies={len(replies)} → _inbox_dump.json")
