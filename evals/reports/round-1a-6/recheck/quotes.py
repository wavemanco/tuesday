"""Task C: quotation check on sonnet/alone/part-5 mock-interview-12.run4, opening paragraph.

Extracts every double-quoted span (straight or curly) and any curly single-quoted span from
the opening invite paragraph of the graded attempt's final assistant text, splits each at
ellipses, and checks each fragment word for word against the invite (ignoring case, curly vs
straight quotes, ** / * / _ emphasis markers, and a full stop just inside the closing mark).
Also checks fragment order inside each quotation, and the order of quotations against each
other. IBAN handling is reported as counts only; nothing of the number is printed.
"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mask as M

PD = "/var/tmp/tuesday-measure/1a6/runs/sonnet/alone/part-5"
STEM = "mock-interview-12.run4"

d = json.load(open(M.EVAL_DIR + "mock-interview.evals.json"))
ev = [e for e in d["evals"] if e["id"] == 12][0]
prompt = ev["prompt"]
a = prompt.index("'Dear Aoife")
b = prompt.index("office manager.'") + len("office manager.")
invite = prompt[a + 1:b]
IBAN = list(M.ibans()[("mock-interview", 12)])[0]


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"\*\*|\*|(?<!\w)_|_(?!\w)", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


ninv = norm(invite)

# the paragraph: from the .md transcript, the first paragraph after the pre-tool note
md = open(os.path.join(PD, STEM + ".md"), encoding="utf-8").read()
paras = [p for p in md.split("\n\n")]
# line 1 of the .md is the pre-tool note (separate text block); paragraph = text block that opens the final message
meta = json.load(open(os.path.join(PD, STEM + ".meta.json")))
inv = meta["invocations"][meta["graded_invocation"]]
texts = []
for line in open(os.path.join(PD, inv["stream"]), encoding="utf-8"):
    try:
        e = json.loads(line)
    except Exception:
        continue
    if e.get("type") == "assistant":
        for blk in e["message"]["content"]:
            if blk.get("type") == "text":
                texts.append(blk["text"])
final = texts[-1]
para = final.split("\n\n")[0]
print("text blocks in graded attempt:", len(texts), "| opening paragraph chars:", len(para))
print("paragraph is in .md transcript:", para in md)

spans = []
for m in re.finditer(r'"([^"]*)"|“([^”]*)”|‘([^’]*)’', para):
    q = next(g for g in m.groups() if g is not None)
    spans.append((m.start(), q))
print("quotations found:", len(spans))

positions = []
for k, (pos, q) in enumerate(spans, 1):
    frags = [f for f in re.split(r"\.\.\.|…", q)]
    nf = [norm(f) for f in frags]
    if nf and nf[-1].endswith(".") and not ninv.endswith(nf[-1]):
        nf[-1] = nf[-1][:-1].rstrip()
    res = []
    last = -1
    in_order = True
    first_pos = None
    for f in nf:
        if not f:
            res.append(("<empty after cut>", True))
            continue
        i = ninv.find(f, last + 1 if last >= 0 else 0)
        found_any = f in ninv
        if i < 0 and found_any:
            in_order = False
            i = ninv.find(f)
        res.append((f, found_any))
        if i >= 0:
            if first_pos is None:
                first_pos = i
            last = i
    positions.append(first_pos)
    # IBAN check on this quotation (counts only)
    nq = M.norm(q)
    longest = 0
    for x in range(len(IBAN)):
        for y in range(x + 1, len(IBAN) + 1):
            if IBAN[x:y] in nq and y - x > longest:
                longest = y - x
    whole = IBAN in nq
    mentions_iban = "iban" in nq
    # characters of the number that follow the word IBAN before the ellipsis
    after = None
    mm = re.search(r"(?i)iban\s*([^.…]*)(\.\.\.|…)", q)
    if mm:
        after = len(M.norm(mm.group(1)))
    print("Q%d: %d fragment(s); word-for-word: %s; fragments in invite order: %s; invite offset of first fragment: %s"
          % (k, len(frags), all(ok for _, ok in res), in_order, first_pos))
    print("    text: " + M.mask('"' + q + '"'))
    if mentions_iban:
        print("    IBAN: whole number present=%s; characters of the number between 'IBAN' and the ellipsis=%s; longest run of the number's characters anywhere in the quotation=%d (runs under 3 are ordinary letters such as an 'ie' inside a word)"
              % (whole, after, longest))
    else:
        print("    no IBAN mention; longest run of the number's characters=%d (%s)" % (longest, "coincidental, under 3" if longest < 3 else "CHECK"))
print("quotations in invite order across the paragraph:", positions == sorted(positions), "| first-fragment offsets in paragraph order:", positions)
