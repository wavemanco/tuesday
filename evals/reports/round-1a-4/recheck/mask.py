"""Masking helper: every script that prints material imports this and passes
all printed text through mask(). It loads the planted IBAN from the frozen eval
file (never printing it) and masks it, any 4+ char piece of it, IBAN-shaped
strings, long digit runs, PPS-shaped IDs and non-.example emails."""
import json, re

EVALS = "/var/tmp/tuesday-measure/1a4/frozen/cases/candidate/mock-interview.evals.json"
IBAN_RE = re.compile(r"\bIE\s*\d{2}(?:[\s-]*[A-Z0-9]){4,30}", re.I)


def norm(s):
    return re.sub(r"[\s\-]", "", s).upper()


def _load_iban():
    data = json.load(open(EVALS))
    blob = json.dumps(data, ensure_ascii=False)
    cands = set()
    for m in IBAN_RE.finditer(blob):
        n = norm(m.group(0))
        if len(n) >= 18:
            cands.add(n[:22])
    return sorted(cands)


IBANS = _load_iban()
IBAN = IBANS[0] if IBANS else None

SEP = r"[\s\-]*"
_BANK = re.compile(r"\b" + re.escape(IBAN[4:8]) + r"\b", re.I) if IBAN else None
_SUBS = set()
if IBAN:
    for i in range(len(IBAN)):
        for j in range(i + 4, len(IBAN) + 1):
            _SUBS.add(IBAN[i:j])


def _mask_pieces(text):
    """Mark every stretch of text whose separator-free, upper-cased form
    holds 4+ consecutive characters of the IBAN, and replace it."""
    if not IBAN:
        return text
    idx = [k for k, ch in enumerate(text) if ch.isalnum()]
    nt = "".join(text[k].upper() for k in idx)
    # only spaces/dashes count as separators when joining characters
    marked = [False] * len(nt)
    for j in range(len(nt)):
        L = 0
        for l in range(4, min(len(IBAN), len(nt) - j) + 1):
            if nt[j:j + l] in _SUBS:
                # characters must be joined only by spaces/dashes in the original
                a, b = idx[j], idx[j + l - 1]
                if re.fullmatch(r"[A-Za-z0-9\s\-]*", text[a:b + 1]):
                    L = l
            else:
                break
        for q in range(j, j + L):
            marked[q] = True
    out, k, n = [], 0, 0
    spans = []
    q = 0
    while q < len(nt):
        if marked[q]:
            r = q
            while r + 1 < len(nt) and marked[r + 1]:
                r += 1
            spans.append((idx[q], idx[r] + 1))
            q = r + 1
        else:
            q += 1
    for a, b in reversed(spans):
        text = text[:a] + "[IBAN-PIECE]" + text[b:]
    return text


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@([A-Za-z0-9\-]+\.)+[A-Za-z]{2,}")
PPS_RE = re.compile(r"\b\d{7}[A-Za-z]{1,2}\b")
LONGDIG_RE = re.compile(r"\b\d(?:[\s\-]?\d){8,}\b")
# Changed on 27 November, after the run, for code scanning. The pattern the reader ran,
#   \b[A-Z]{2}\d{2}(?:[\s\-]?[A-Z0-9]{2,4}){3,}\b
# backtracks exponentially on a long run of capitals followed by a word character. The
# pattern below matches the same spans: checked on every string of up to 7 characters
# over "A0 -a._" and a newline after "GB00", and on 300,000 random strings.
IBANISH_RE = re.compile(r"\b[A-Z]{2}\d{2}[\s\-]?(?:[A-Z0-9]{6,}|[A-Z0-9]{4,5}[\s\-][A-Z0-9]{2,}"
                        r"|[A-Z0-9]{2,3}[\s\-][A-Z0-9]{4,}|[A-Z0-9]{2,3}[\s\-][A-Z0-9]{2,3}[\s\-][A-Z0-9]{2,})"
                        r"(?:[\s\-][A-Z0-9]{2,})*\b")


def mask(text):
    if not isinstance(text, str):
        text = str(text)
    text = _mask_pieces(text)
    text = re.sub(r"check digits\s*\d+", "check digits [MASKED]", text, flags=re.I)
    text = IBAN_RE.sub("[IBAN-LIKE]", text)
    text = IBANISH_RE.sub("[IBAN-LIKE]", text)
    if _BANK is not None:
        text = _BANK.sub("[BANKCODE]", text)
    text = re.sub(r"\bIE\s?\d{2}\b", "[IBAN-START]", text)

    def em(m):
        s = m.group(0)
        return s if s.lower().endswith(".example") or ".example" in s.lower().split("@")[-1] else "[EMAIL]"
    text = EMAIL_RE.sub(em, text)
    text = PPS_RE.sub("[ID]", text)
    text = LONGDIG_RE.sub("[LONG-NUMBER]", text)
    return text


if __name__ == "__main__":
    print("IBAN candidates found:", len(IBANS), "length of first:", len(IBAN) if IBAN else None)
