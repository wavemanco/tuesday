"""Shared expectation clauses: one wording per rule, however many fixtures grade it.

A rule that several fixtures grade used to be written into each expectation by
hand — the accounting labels eight times, the question-premise rule eight times,
the count ban three times — and every change to the rule reached some copies and
not others. The skill then said one thing and a grader read another on the same
run. A clause is now defined once, under the top-level `"clauses"` key of a
skill's evals.json, and an expectation includes it as `{{name}}`. Everything that
reads a fixture — the eval runner, the CI gate, the self-tests — reads it through
`load_cases`, so what a grader is shown is the expanded text and nothing else.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CLAUSE_REF = re.compile(r"\{\{([a-z0-9_]+)\}\}")
EXPANDED_FIELDS = ("expectations", "expected_output")


class ClauseError(ValueError):
    """A fixture names a clause its file does not define."""


def expand_text(text: str, clauses: dict[str, str], where: str) -> str:
    def swap(match: re.Match) -> str:
        name = match.group(1)
        if name not in clauses:
            raise ClauseError(f"{where}: {{{{{name}}}}} names no clause in this file's \"clauses\"")
        return clauses[name]
    return CLAUSE_REF.sub(swap, text)


def expand_spec(spec) -> list[dict]:
    """The cases of a parsed evals.json, with every clause reference expanded."""
    if isinstance(spec, list):
        return spec
    clauses = spec.get("clauses") or {}
    if not isinstance(clauses, dict) or any(not isinstance(v, str) for v in clauses.values()):
        raise ClauseError("\"clauses\" must map names to strings")
    cases = spec.get("evals")
    if not isinstance(cases, list):
        return cases
    out = []
    for case in cases:
        if not isinstance(case, dict):
            out.append(case)
            continue
        case = dict(case)
        label = f"eval {case.get('id')}"
        for field in EXPANDED_FIELDS:
            value = case.get(field)
            if isinstance(value, str):
                case[field] = expand_text(value, clauses, f"{label} {field}")
            elif isinstance(value, list):
                case[field] = [expand_text(v, clauses, f"{label} {field} #{n}") if isinstance(v, str) else v
                               for n, v in enumerate(value, 1)]
        out.append(case)
    return out


def load_cases(path: Path) -> list[dict]:
    """Read an evals.json and return its cases with clauses expanded."""
    return expand_spec(json.loads(Path(path).read_text(encoding="utf-8")))


def unused_clauses(spec) -> list[str]:
    """Clause names defined but never referenced — dead text a reader would trust."""
    if not isinstance(spec, dict):
        return []
    used = set()
    for case in spec.get("evals") or []:
        if not isinstance(case, dict):
            continue
        for field in EXPANDED_FIELDS:
            value = case.get(field)
            for text in ([value] if isinstance(value, str) else value if isinstance(value, list) else []):
                if isinstance(text, str):
                    used.update(CLAUSE_REF.findall(text))
    return sorted(set(spec.get("clauses") or {}) - used)
