#!/usr/bin/env python3
"""A search engine with a fixed corpus, served to a clean room over MCP stdio.

Every research expectation in this suite used to be graded from rooms where search
was present and refused, so `unavailable` was the only label any run could earn
truthfully, and `yes` and `skipped` were never measured at all. Live search would
measure them and would also make every run depend on what the web returned that
day. This serves a fixture's own pages instead — the same answer to the same query
every time — and keeps its own record of every call, so what the response says it
researched can be checked against what was actually asked, independently of the
model's account of it.

Usage (the harness writes both paths; never run from inside a room):

    python3 -I research_server.py <corpus.json> <calls.jsonl>

Three properties are deliberate:

- **Pages score on their declared keywords only, with the fixture's entity tokens
  removed from both sides.** The prototype scored on title and text with a
  two-token overlap, so the company's name plus any one common word surfaced every
  page — a run that searched only the company's name then "found" the interview
  process, and wrote `yes` for a target it never aimed at. Here the company name
  alone surfaces nothing, so what a call returned is evidence of what it was
  aimed at.
- **A miss is an ordinary answer, never an error.** The prototype answered an
  unknown URL with "Fetch failed: 404", and a run can fairly read "failed" as a
  refusal and label the target `unavailable`. A call that ran and found nothing is
  a call that ran; a server error is reserved for the server breaking, which the
  harness treats as a broken room rather than a skill outcome.
- **It writes only to the log path it is given.** Claude Code starts the server
  with the room as its working directory, and the harness collects every text file
  in the room as something the response produced. A log or a cache written beside
  it would be graded as the skill's output.

Transport: newline-delimited JSON-RPC 2.0 on stdin/stdout; exits on stdin EOF.
"""

from __future__ import annotations

import json
import re
import sys

# Small on purpose: a stopword that is also a page keyword ("about" for an About
# page) would make that page unreachable by any query.
STOPWORDS = frozenset("""
a an and are as at be by for from how in is it its of on or the to what when where
which who why with
""".split())

SNIPPET = 300
TOP = 5

TOOLS = [
    {"name": "search",
     "description": "Search the public web. Returns up to 5 results, each with a title, "
                    "a URL and a snippet of the page.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}},
                     "required": ["query"]}},
    {"name": "fetch",
     "description": "Fetch a web page by URL and return its text.",
     "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}},
                     "required": ["url"]}},
]


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(text).lower()))


def scoring_tokens(text: str, entity: set[str]) -> set[str]:
    return tokens(text) - STOPWORDS - entity


def same_url(a: str, b: str) -> bool:
    return str(a).strip().rstrip("/") == str(b).strip().rstrip("/")


def search(corpus: dict, query: str) -> tuple[str, list[dict]]:
    """Return (the text the model sees, the pages returned), deterministically."""
    entity = set().union(*(tokens(t) for t in corpus.get("entity_tokens", []))) \
        if corpus.get("entity_tokens") else set()
    wanted = scoring_tokens(query, entity)
    scored = []
    for page in corpus.get("pages", []):
        keywords = set().union(*(scoring_tokens(k, entity) for k in page.get("keywords", []))) \
            if page.get("keywords") else set()
        score = len(wanted & keywords)
        if score >= 1:
            scored.append((-score, page.get("url", ""), page))
    scored.sort(key=lambda item: (item[0], item[1]))
    hits = [page for _, _, page in scored[:TOP]]
    if not hits:
        return f'No results found for "{query}".', []
    lines = [f'Search results for "{query}":']
    for i, page in enumerate(hits, 1):
        lines.append(f"{i}. {page.get('title', '')}\n   {page.get('url', '')}\n"
                     f"   {page.get('text', '')[:SNIPPET]}")
    return "\n".join(lines), hits


def fetch(corpus: dict, url: str) -> tuple[str, list[dict]]:
    for page in corpus.get("pages", []):
        if same_url(page.get("url", ""), url):
            return f"{page.get('title', '')}\n{page.get('url', '')}\n\n{page.get('text', '')}", [page]
    return f"No page at {url}", []


def target_tags(pages: list[dict]) -> list:
    return sorted({p["target"] for p in pages if p.get("target") is not None}, key=str)


class Server:
    def __init__(self, corpus: dict, log_path: str, out=None):
        self.corpus = corpus
        self.log_path = log_path
        self.out = out or sys.stdout

    def log(self, record: dict) -> None:
        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def reply(self, id_, result=None, error=None) -> None:
        message = {"jsonrpc": "2.0", "id": id_}
        if error is not None:
            message["error"] = error
        else:
            message["result"] = result
        self.out.write(json.dumps(message) + "\n")
        self.out.flush()

    def handle(self, request: dict) -> None:
        method, id_ = request.get("method"), request.get("id")
        params = request.get("params") or {}
        if id_ is None:
            return                                  # notifications need no answer
        if method == "initialize":
            self.log({"rpc": "initialize", "protocolVersion": params.get("protocolVersion")})
            self.reply(id_, {"protocolVersion": params.get("protocolVersion", "2024-11-05"),
                             "capabilities": {"tools": {}},
                             "serverInfo": {"name": "web", "version": "1"}})
        elif method == "tools/list":
            self.log({"rpc": "tools/list"})
            self.reply(id_, {"tools": TOOLS})
        elif method == "ping":
            self.reply(id_, {})
        elif method == "tools/call":
            name, args = params.get("name"), params.get("arguments") or {}
            if name == "search":
                text, pages = search(self.corpus, str(args.get("query", "")))
                outcome = "hit" if pages else "no_results"
            elif name == "fetch":
                text, pages = fetch(self.corpus, str(args.get("url", "")))
                outcome = "hit" if pages else "fetch_miss"
            else:
                self.reply(id_, error={"code": -32602, "message": f"unknown tool {name}"})
                return
            self.log({"id": id_, "tool": name, "args": args,
                      "returned_urls": [p.get("url") for p in pages],
                      "targets": target_tags(pages), "outcome": outcome})
            self.reply(id_, {"content": [{"type": "text", "text": text}], "isError": False})
        else:
            self.reply(id_, error={"code": -32601, "message": f"method not found: {method}"})


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.stderr.write("usage: research_server.py <corpus.json> <calls.jsonl>\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        corpus = json.load(handle)
    server = Server(corpus, argv[2])
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(request, dict):
            server.handle(request)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
