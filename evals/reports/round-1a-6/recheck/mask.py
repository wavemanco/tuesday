"""Masker shared by the recheck scripts.

Protected values come from the evals' own "sentinels" (never printed).
mask(text) replaces:
  - any span whose space/dash-stripped, lowercased form contains a 4+ char
    substring of a protected value (IBANs, government IDs, registrations)
  - anything shaped like an Irish IBAN start: "IE" + optional space/dash + digit ...
  - digit runs of 4+ (a lone 4-digit year 1900-2099 is kept unless it is a piece
    of a protected value)
  - alphanumeric tokens of length 6+ mixing letters and 2+ digits
  - email addresses whose domain does not end in ".example"
check_clean(text) raises if any protected piece survives.
"""
import json
import re

EVAL_DIR = "/var/tmp/tuesday-measure/1a6/frozen/cases/candidate/"
SEP = set(" -   ‐‑‒–—\t")


def norm(s):
    return "".join(c for c in s.lower() if c not in SEP)


def _load():
    prot = {}  # normalized value -> (skill, id, kind)
    for f in ("job-underwriter.evals.json", "mock-interview.evals.json"):
        d = json.load(open(EVAL_DIR + f))
        for e in d["evals"]:
            for s in e.get("sentinels", []):
                for sp in s["spellings"]:
                    prot[norm(sp)] = (f.split(".")[0], e["id"], s["kind"])
    return prot


PROTECTED = _load()


def ibans():
    """Return {('mock-interview',12): normalized_iban, ('job-underwriter',8): ...}"""
    out = {}
    for v, (sk, i, kind) in PROTECTED.items():
        if kind == "protected_value":
            out.setdefault((sk, i), set()).add(v)
    return out


def _normmap(text):
    chars, idx = [], []
    for i, c in enumerate(text):
        if c in SEP:
            continue
        chars.append(c.lower())
        idx.append(i)
    return "".join(chars), idx


def protected_spans(text, k=4):
    n, idx = _normmap(text)
    spans = []
    grams = set()
    for v in PROTECTED:
        for j in range(len(v) - k + 1):
            grams.add(v[j:j + k])
    for j in range(len(n) - k + 1):
        if n[j:j + k] in grams:
            spans.append((idx[j], idx[j + k - 1] + 1))
    return spans


IBAN_START = re.compile(r"(?i)(?<![a-z])ie[ \- ]?\d(?:[ \- ]?[0-9a-z])*")
DIGITS = re.compile(r"\d{4,}")
MIXED = re.compile(r"\b(?=[A-Za-z0-9]*\d[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{6,}\b")
EMAIL = re.compile(r"[\w.+\-]+@([\w\-]+(?:\.[\w\-]+)+)")
CONTEXT_KW = re.compile(r"(?i)\b(iban|check[\s\-]*digits?|checksum|account|acct|sort[\s\-]*code|bic|swift|"
                        r"ending|ends?\s+(?:in|with)|digits?|characters?|starts?\s+with|starting|begins?\s+with|"
                        r"prefix|licen[cs]e|registration|pps|passport|ssn|social\s+security|ieins?|id\s+number)\b")


def mask(text):
    if not isinstance(text, str):
        text = str(text)
    flags = [False] * len(text)

    def mark(a, b):
        for i in range(a, b):
            flags[i] = True

    for a, b in protected_spans(text):
        mark(a, b)
    for m in IBAN_START.finditer(text):
        mark(m.start(), m.end())
    for m in DIGITS.finditer(text):
        s = m.group(0)
        if len(s) == 4 and 1900 <= int(s) <= 2099:
            continue
        mark(m.start(), m.end())
    for m in MIXED.finditer(text):
        mark(m.start(), m.end())
    for m in EMAIL.finditer(text):
        if not m.group(1).lower().endswith(".example"):
            mark(m.start(), m.end())
    # context rule (added after a slip where two check digits printed): every digit run within
    # 120 chars after an account/IBAN/digit-describing keyword is masked, however short
    for m in CONTEXT_KW.finditer(text):
        w0, w1 = m.end(), min(len(text), m.end() + 120)
        for d in re.finditer(r"\d+", text[w0:w1]):
            mark(w0 + d.start(), w0 + d.end())
    out, i = [], 0
    while i < len(text):
        if flags[i]:
            j = i
            while j < len(text) and flags[j]:
                j += 1
            out.append("[#]")
            i = j
        else:
            out.append(text[i])
            i += 1
    res = "".join(out)
    check_clean(res)
    return res


class Leak(Exception):
    pass


def check_clean(text):
    if protected_spans(text):
        raise Leak("protected piece survived masking")
    if IBAN_START.search(text):
        raise Leak("IBAN-shaped start survived masking")
    for m in EMAIL.finditer(text):
        if not m.group(1).lower().endswith(".example"):
            raise Leak("email survived masking")
    return True
