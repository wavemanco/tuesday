"""Print the assistant-authored blocks of a stream-json transcript, masked.
usage: python3 -I stream_dump.py STREAM.jsonl [--users]
Prints: line number, event type, block type, tool name, then text / tool input.
With --users, also prints the first 200 chars of user events (tool results)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mask import mask

path = sys.argv[1]
users = "--users" in sys.argv
for ln, raw in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
    raw = raw.strip()
    if not raw:
        continue
    try:
        ev = json.loads(raw)
    except Exception:
        print(f"{ln}: <unparsable>")
        continue
    t = ev.get("type")
    if t == "assistant":
        for b in ev.get("message", {}).get("content", []):
            bt = b.get("type")
            if bt == "text":
                print(f"--- L{ln} assistant text ---\n{mask(b['text'])}")
            elif bt == "tool_use":
                print(f"--- L{ln} assistant tool_use {b.get('name')} ---\n{mask(json.dumps(b.get('input'), ensure_ascii=False, indent=1))}")
            elif bt == "thinking":
                print(f"--- L{ln} assistant thinking (len {len(b.get('thinking',''))}) ---")
    elif t == "user" and users:
        c = ev.get("message", {}).get("content")
        if isinstance(c, list):
            for b in c:
                if b.get("type") == "tool_result":
                    cc = b.get("content")
                    s = cc if isinstance(cc, str) else json.dumps(cc, ensure_ascii=False)
                    print(f"--- L{ln} user tool_result: {mask(s[:200])!r}")
                elif b.get("type") == "text":
                    print(f"--- L{ln} user text: {mask(b['text'][:200])!r}")
        elif isinstance(c, str):
            print(f"--- L{ln} user str: {mask(c[:200])!r}")
    elif t == "result":
        print(f"--- L{ln} result: {mask(str(ev.get('result',''))[:300])!r}")
