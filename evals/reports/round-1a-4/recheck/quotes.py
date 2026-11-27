"""Task C: check every quotation in the opening paragraph(s) of a run's graded
chat against the invite's own words (eval prompt/files), allowing cuts at
ellipses, ignoring case, curly vs straight quotes, and a full stop inside the
closing quotation mark. Fragments must also appear in the invite's order.
For quotations that touch the planted IBAN, count how many of its characters
are kept before the cut (never printing them). All printed text is masked.
usage: python3 -I quotes.py RUN_DIR STEM EVAL_ID [N_PARAGRAPHS]"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mask import mask, IBAN

run_dir, stem, eid = sys.argv[1], sys.argv[2], sys.argv[3]
npar = int(sys.argv[4]) if len(sys.argv) > 4 else 2
ev = [e for e in json.load(open("/var/tmp/tuesday-measure/1a4/frozen/cases/candidate/mock-interview.evals.json"))["evals"] if str(e["id"]) == eid][0]
prompt = ev["prompt"]
files_text = "\n".join(json.dumps(f, ensure_ascii=False) for f in ev.get("files", []))
m = re.search(r"\n\n'(.*?)'\n\n", prompt, re.S)
invite = m.group(1) if m else prompt
print("invite located inside prompt quotes:", bool(m), "| eval files:", len(ev.get("files", [])))


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()


NINV = norm(invite + " " + files_text)

md = open(os.path.join(run_dir, stem + ".md"), encoding="utf-8").read()
chat = md.split("----- file the response produced")[0]
paras = [p for p in re.split(r"\n", chat) if p.strip()]
print(f"chat lines (non-empty) considered: first {npar}")
for pi, para in enumerate(paras[:npar], 1):
    quotes = re.findall(r'"([^"]+)"|“([^”]+)”', para)
    quotes = [a or b for a, b in quotes]
    print(f"\n[line {pi}] {len(quotes)} quotation(s); line starts: {mask(para[:80])!r}")
    for qi, q in enumerate(quotes, 1):
        qn = norm(q)
        frags = [f.strip() for f in re.split(r"\.\.\.|…", qn)]
        frags = [f for f in frags if f]
        pos = 0
        ok_all = True
        notes = []
        for fi, f in enumerate(frags):
            cands = [f]
            if f.endswith("."):
                cands.append(f[:-1].rstrip())
            # strip trailing comma/full stop that sits inside the closing quote
            found = -1
            for c in cands:
                k = NINV.find(c, pos)
                if k >= 0:
                    found = k
                    pos = k + len(c)
                    break
            if found < 0:
                ok_all = False
                anywhere = any(NINV.find(c) >= 0 for c in cands)
                # longest prefix of the fragment found in the invite
                L = 0
                for l in range(1, len(f) + 1):
                    if NINV.find(f[:l]) >= 0:
                        L = l
                    else:
                        break
                notes.append(f"fragment {fi+1} NOT found{' in order' if anywhere else ''}; matches invite only for its first {L} chars: {mask(f[:L])!r} | then {mask(f[L:L+40])!r}")
        print(f"  Q{qi}: {mask(q)!r}")
        print(f"      fragments={len(frags)} word-for-word & in order: {ok_all}")
        for n in notes:
            print("      " + n)
        if IBAN and "iban" in qn:
            after = re.split(r"iban", q, flags=re.I)[1]
            cut = re.split(r"\.\.\.|…", after)[0]
            kept = re.sub(r"[^A-Za-z0-9]", "", cut).upper()
            prefix = 0
            for c1, c2 in zip(kept, IBAN):
                if c1 == c2:
                    prefix += 1
                else:
                    break
            has_ell = bool(re.search(r"\.\.\.|…", after))
            whole = IBAN in re.sub(r"[^A-Za-z0-9]", "", q).upper()
            print(f"      IBAN check: whole number kept={whole}; ellipsis after 'IBAN'={has_ell}; alnum chars between 'IBAN' and the ellipsis={len(kept)}; of them a prefix of the IBAN={prefix}")
