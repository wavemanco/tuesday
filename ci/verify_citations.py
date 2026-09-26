#!/usr/bin/env python3
"""Refetch every source in conventions/citations.md and confirm each quotation.

`check_skills.py` proves the citations are internally consistent — every marker
resolves, every entry is used, nothing elsewhere quotes more than an entry holds.
It cannot prove an entry matches its source, because that needs the network and
CI runs without it. This does, by hand:

    python ci/verify_citations.py              # every entry
    python ci/verify_citations.py C3 C15       # just these

Three outcomes per entry, for the reason this repository's harnesses all learned
the hard way: a page that could not be fetched is not a quotation that failed.

    verified     every quoted span in the Verbatim field appears in the source
    NOT FOUND    the source was read and a quoted span is not in it
    unreachable  the source could not be read here — network, paywall, or a PDF
                 with no extractor available — so nothing is known either way

Matching is deliberately forgiving about typography and strict about words:
case, curly quotes, dashes and whitespace are normalised, a quoted `…` stands
for an omission, and a bare footnote number between words in extracted PDF text
is dropped. Every word the entry quotes has to be in the source, in order.
"""

from __future__ import annotations

import html
import io
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TIMEOUT = 40


sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_skills import citation_entries as entries  # noqa: E402
from check_skills import normalise_quote as normalise  # noqa: E402
from check_skills import quote_in as present  # noqa: E402
from check_skills import quoted_spans  # noqa: E402


def fetch(url: str) -> tuple[str | None, str]:
    """Return (normalised text, note). None means the source could not be read."""
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (citation check)"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
            kind = response.headers.get("Content-Type", "")
    except Exception as exc:  # noqa: BLE001 — any failure to read is "unreachable"
        return None, f"{type(exc).__name__}: {exc}"[:140]

    if "pdf" in kind or url.endswith(".pdf") or raw[:4] == b"%PDF" or "/pdf/" in url:
        try:
            from pdfminer.high_level import extract_text
        except ImportError:
            return None, "PDF with no extractor here — pip install pdfminer.six"
        return normalise(extract_text(io.BytesIO(raw))), "pdf"

    page = raw.decode("utf-8", errors="replace")
    page = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    return normalise(page), "html"


def main() -> int:
    wanted = set(sys.argv[1:])
    all_entries = entries()
    unknown = wanted - set(all_entries)
    if unknown:
        print(f"no such citation(s): {', '.join(sorted(unknown))}")
        return 2

    cache: dict[str, tuple[str | None, str]] = {}
    counts = {"verified": 0, "NOT FOUND": 0, "unreachable": 0}
    for cid, fields in all_entries.items():
        if wanted and cid not in wanted:
            continue
        url_match = re.search(r"https?://\S+", fields.get("Source", ""))
        if not url_match:
            # "as C1" — inherit the URL of the entry it points at.
            ref = re.search(r"as (C\d+)", fields.get("Source", ""))
            parent = all_entries.get(ref.group(1), {}) if ref else {}
            url_match = re.search(r"https?://\S+", parent.get("Source", ""))
        spans = quoted_spans(fields.get("Verbatim", ""))
        if not url_match or not spans:
            print(f"  unreachable  {cid}: no URL or no quoted span to check")
            counts["unreachable"] += 1
            continue
        url = url_match.group(0).rstrip(").,")
        if url not in cache:
            cache[url] = fetch(url)
        source, note = cache[url]
        if source is None:
            print(f"  unreachable  {cid}: {note}")
            counts["unreachable"] += 1
            continue
        missing = [s for s in spans if not present(s, source)]
        if missing:
            counts["NOT FOUND"] += 1
            print(f"  NOT FOUND    {cid}: {missing[0][:90]!r}")
        else:
            counts["verified"] += 1
            print(f"  verified     {cid} ({len(spans)} span(s), {note})")

    print(f"\n{counts['verified']} verified, {counts['NOT FOUND']} not found, "
          f"{counts['unreachable']} unreachable")
    if counts["unreachable"]:
        print("Unreachable is not a pass. Those entries are unchecked, not confirmed.")
    return 1 if counts["NOT FOUND"] else 0


if __name__ == "__main__":
    sys.exit(main())
