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
    NOT FOUND    the source was read and a quoted span is not in it     (exit 1)
    MALFORMED    the entry has no quotation, or no URL it can resolve   (exit 1)
    unreachable  the source could not be read here — network, paywall, or a PDF
                 with no extractor available — so nothing is known     (exit 3)

Matching is forgiving about typography and strict about words: case, curly
quotes, dashes and whitespace are normalised and nothing else is. An entry marks
an omission with `…`, and each omission is inspected — it may skip a footnote
number or ordinary words, never a hedge or a negation, and never more than a
dozen words. Nothing is deleted from either side before matching: an earlier
version dropped every short number between two words as a presumed footnote,
which made "7 years" and "9 years" the same quotation.
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
from check_skills import quote_tokens  # noqa: E402
from check_skills import quote_in_source  # noqa: E402
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
        return extract_text(io.BytesIO(raw)), "pdf"

    page = raw.decode("utf-8", errors="replace")
    page = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    return html.unescape(page), "html"


def main() -> int:
    wanted = set(sys.argv[1:])
    all_entries = entries()
    unknown = wanted - set(all_entries)
    if unknown:
        print(f"no such citation(s): {', '.join(sorted(unknown))}")
        return 2

    cache: dict[str, tuple[str | None, str]] = {}
    counts = {"verified": 0, "NOT FOUND": 0, "unreachable": 0, "MALFORMED": 0}
    for cid, fields in all_entries.items():
        if wanted and cid not in wanted:
            continue
        # Resolve "as C1" to the entry it names, and treat a broken chain as a
        # defect in this file rather than as a network problem: calling it
        # "unreachable" filed a malformed entry under a heading that means
        # "unchecked, try again later".
        source_field, seen = fields.get("Source", ""), {cid}
        url_match = re.search(r"https?://\S+", source_field)
        while not url_match:
            ref = re.search(r"as (C\d+)", source_field)
            if not ref or ref.group(1) in seen or ref.group(1) not in all_entries:
                break
            seen.add(ref.group(1))
            source_field = all_entries[ref.group(1)].get("Source", "")
            url_match = re.search(r"https?://\S+", source_field)
        spans = quoted_spans(fields.get("Verbatim", ""))
        if not url_match or not spans:
            print(f"  MALFORMED    {cid}: {'no quoted span' if not spans else 'no URL, and no resolvable as-Cn'}")
            counts["MALFORMED"] += 1
            continue
        url = url_match.group(0).rstrip(").,")
        if url not in cache:
            cache[url] = fetch(url)
        source, note = cache[url]
        if source is None:
            print(f"  unreachable  {cid}: {note}")
            counts["unreachable"] += 1
            continue
        failures = [why for ok, why in (quote_in_source(s, source) for s in spans) if not ok]
        if failures:
            counts["NOT FOUND"] += 1
            print(f"  NOT FOUND    {cid}: {failures[0]}")
        else:
            counts["verified"] += 1
            print(f"  verified     {cid} ({len(spans)} span(s), {note})")

    print(f"\n{counts['verified']} verified, {counts['NOT FOUND']} not found, "
          f"{counts['unreachable']} unreachable, {counts['MALFORMED']} malformed")
    # Exit codes keep the three outcomes apart for anything scripting this. An
    # unreachable source is not a pass, and exiting 0 on "18 unreachable" — as the
    # first version did with no network — reads as one to every caller.
    if counts["NOT FOUND"] or counts["MALFORMED"]:
        return 1
    if counts["unreachable"]:
        print("Unreachable is not a pass. Those entries are unchecked, not confirmed.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
