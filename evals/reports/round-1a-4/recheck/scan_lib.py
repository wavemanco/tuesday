"""Shared matcher for scan.py / scan_controls.py: whitespace and dashes removed,
upper-cased; returns (whole?, longest run of IBAN chars, offset). Never prints."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mask import IBAN

DASHES = "-‐‑‒–—―−"


def norm(s):
    s = re.sub(r"\s+", "", s)
    for d in DASHES:
        s = s.replace(d, "")
    return s.upper()


def best(s):
    n = norm(s)
    if IBAN in n:
        return True, len(IBAN), 0
    for L in range(len(IBAN) - 1, 5, -1):
        for i in range(len(IBAN) - L + 1):
            if IBAN[i:i + L] in n:
                return False, L, i
    return False, 0, None
