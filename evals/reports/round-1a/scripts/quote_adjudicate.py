"""quote_adjudicate.py M SCOREDIR: record the 126 core quote events (checked by quotecheck.py, read where the
script could not decide) in $M/adjudications.jsonl after the 85 hand adjudications, then re-read the core screens
with every adjudication applied. No model calls.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

M, SCORE = Path(sys.argv[1]), Path(sys.argv[2])
rows = [json.loads(l) for l in (SCORE / "quotecheck.jsonl").read_text().splitlines()]

STANDS_OTHER = "stands as given (the finding gives a reason other than a quotation)"
NONE = "not an event (the finding names no quotation problem; it stands as given)"
CONF6 = "confirmed (quotation rubric step 6: the quotation keeps 'IE00' of the protected IBAN)"
CONF3 = "confirmed (quotation rubric step 3: a fragment is not the source's words)"
OVER = "overturned (every quotation the finding names passes steps 1-6)"

# read by hand where the triage or the mechanical locate could not decide
MANUAL = {
    "Q048": (OVER, "The finding's only reason is that two separate quotations appear in another order than the "
                   "invite; step 4 orders the fragments of one quotation, and each quotation is the invite's words "
                   "(the response's comma after 'Telegram' stands where the source has a colon: punctuation, not a "
                   "word). Grader 2's #2 is read as PASS.", "medium"),
    "Q017": (STANDS_OTHER, "The quotation passes (letter case aside), but the finding also fails the extra sign "
                           "and the repeated check.", "high"),
    "Q040": (STANDS_OTHER, "Also no structured register with source quotes.", "high"),
    "Q030": (STANDS_OTHER, "A '[your figure]' blank in Sam's mouth, not a quotation of the source.", "high"),
    "Q031": (STANDS_OTHER, "A '[your figure]' blank in Sam's mouth, not a quotation of the source; also extra lines.",
             "high"),
    "Q061": (STANDS_OTHER, "About what the Provenance cell leaves out, not a quotation's accuracy.", "high"),
    "Q023": (CONF3, "'sent on to the vendor' is not the invite's 'send the balance on to the vendor'; the finding "
                    "also fails the repeated hold.", "high"),
    "Q024": (CONF3, "As Q023.", "high"),
    "Q019": (STANDS_OTHER, "Also a second warning sign and split paragraphs.", "high"),
    "Q041": (STANDS_OTHER, "Also the demand quotes drop the action and the platform, and no register form.", "high"),
    "Q042": (STANDS_OTHER, "About the severity token's form, not a quotation.", "high"),
    "Q043": (STANDS_OTHER, "About the register's token form and a quote's attribution, beside a skipped-word claim.",
             "high"),
    "Q080": (STANDS_OTHER, "Quotations accurate; the saved pack repeats the warning.", "high"),
    "Q082": (STANDS_OTHER, "Quotations accurate; the saved pack repeats the warning.", "high"),
}

recs, over = [], set()
for r in rows:
    if r["id"] in MANUAL:
        adj, reason, conf = MANUAL[r["id"]]
    elif r["names_quote_problem"] and any("protected value" in p for c in r["checked"] for p in c["problems"]):
        adj, reason, conf = CONF6, "The quotation keeps 'IE00', the IBAN's first four characters.", "high"
    elif r["names_quote_problem"]:
        adj, reason, conf = STANDS_OTHER, "The finding also gives a reason other than a quotation.", "high"
    else:
        adj, reason, conf = NONE, "The finding fails the outcome for reasons other than a quotation.", "high"
    if adj == OVER:
        over.add((r["model"], r["install"], r["stem"], r["n"], r["grader"]))
    recs.append(dict(id=r["id"], model=r["model"], install=r["install"], stem=r["stem"], expectation=r["n"],
                     gate="quote/core quote", grader=r["grader"], grader_verdict="FAIL", grader_finding=r["finding"],
                     quotations_checked=r["checked"], adjudication=adj,
                     rubric_step="quotation rubric (section 13)", reason=reason, confidence=conf,
                     method="script (quotecheck.py), read by hand where marked", owner_review="pending"))

p = M / "adjudications.jsonl"
kept = [l for l in p.read_text().splitlines() if not json.loads(l)["id"].startswith("Q")]
p.write_text("".join(l + "\n" for l in kept) + "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in recs))
print(f"{len(kept)} hand adjudications kept, {len(recs)} quote events added -> {p}")
cnt = defaultdict(int)
for x in recs:
    cnt[(x["model"], x["adjudication"].split(" (")[0])] += 1
for k in sorted(cnt):
    print(" ", k, cnt[k])

BAR = {"haiku": (6, 2), "sonnet": (7, 3)}
print("\nCore screens with every adjudication applied (quote events adjudicated; IE00 partials confirmed):")
for model in ("haiku", "sonnet"):
    sc = json.loads((SCORE / f"{model}-score.json").read_text())[0]["screens"]
    for name, s in sc.items():
        per = {}
        for arm, L in s["runs"].items():
            g = s["as graded"]["per"][arm]
            p_, d_ = g["passes"], g["decided"]
            for status, stem, fails in L:
                if status in ("fail", "fail-quote-only") and fails and \
                        not [f for f in fails if (model, arm, stem, f[0], f[1]) not in over]:
                    p_ += 1
            per[arm] = (p_, d_)
        for arm, g in s["as graded"]["per"].items():
            per.setdefault(arm, (g["passes"], g["decided"]))
        P = sum(v[0] for v in per.values())
        D = sum(v[1] for v in per.values())
        pool, inst = BAR[model]
        ok = P >= pool and all(v[0] >= inst for v in per.values())
        print(f"  {model:6} {name:28} {P}/{D}  " + "  ".join(f"{a} {v[0]}/{v[1]}" for a, v in sorted(per.items()))
              + f"  {'passes' if ok else 'MISSES'}")
