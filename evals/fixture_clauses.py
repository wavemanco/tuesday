"""Shared expectation clauses: one wording per rule, however many fixtures grade it.

A rule that several fixtures grade used to be written into each expectation by
hand — the accounting labels eight times, the question-premise rule eight times,
the count ban three times — and every change to the rule reached some copies and
not others. The skill then said one thing and a grader read another on the same
run. A clause is now defined once, under the top-level `"clauses"` key of a
skill's evals.json, and an expectation includes it as `{{name}}`. Everything that
reads a fixture — the eval runner, the CI gate, the self-tests — reads it through
`load_cases`, so what a grader is shown is the expanded text and nothing else.

A fixture whose test turns on how old something is when the run reads it writes
those dates relative to the run, `{{date-4m:month year}}`, because an absolute
date ages: mock-interview eval 8's interviews were "on 21 October", and every run
after that date was shown interviews already past (evals/README.md, "Dates
relative to the run"). `dated` writes them out for one run's date, or for the
fixture's `date_anchor` when the run recorded none.
"""

from __future__ import annotations

import calendar
import datetime
import json
import re
from pathlib import Path

CLAUSE_REF = re.compile(r"\{\{([a-z0-9_]+)\}\}")
EXPANDED_FIELDS = ("expectations", "expected_output")

# A date relative to the run: offsets in days, months or years, applied in the order
# written, then one of four forms. `{{date:day month year}}` is the run's own date.
DATE_FORMS = ("day month year", "day month", "month year", "year")
DATE_REF = re.compile(r"\{\{date((?:[+-]\d+[dmy])*):(" + "|".join(DATE_FORMS) + r")\}\}")
DATE_OPEN = "{{date"
DATE_ANCHOR = "date_anchor"
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")


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


def clause_refs(path: Path) -> dict:
    """{case id: [the clause names each expectation includes, in order]}, read from an evals.json
    before expansion: which expectations grade a rule written once (compare_arms' truthfulness
    rows read them)."""
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = spec.get("evals") if isinstance(spec, dict) else spec
    return {case.get("id"): [sorted(set(CLAUSE_REF.findall(e))) if isinstance(e, str) else []
                             for e in case.get("expectations") or []]
            for case in cases or [] if isinstance(case, dict)}


def shifted(day: datetime.date, offsets: str) -> datetime.date:
    """`day` moved by each offset in turn (`+9d`, `-4m`, `+1y`); a month or year step keeps the
    day of the month where the month has it, else its last day."""
    for amount, unit in re.findall(r"([+-]\d+)([dmy])", offsets):
        if unit == "d":
            day += datetime.timedelta(days=int(amount))
            continue
        months = day.year * 12 + day.month - 1 + int(amount) * (12 if unit == "y" else 1)
        year, month = divmod(months, 12)
        day = day.replace(year=year, month=month + 1,
                          day=min(day.day, calendar.monthrange(year, month + 1)[1]))
    return day


def written(day: datetime.date, form: str) -> str:
    """A date in one of DATE_FORMS: "12 October 2026", "12 October", "October 2026", "2026"."""
    return {"day month year": f"{day.day} {MONTHS[day.month - 1]} {day.year}",
            "day month": f"{day.day} {MONTHS[day.month - 1]}",
            "month year": f"{MONTHS[day.month - 1]} {day.year}",
            "year": str(day.year)}[form]


def strings_of(value) -> list[str]:
    """Every string in a case, however deep."""
    if isinstance(value, str):
        return [value]
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [s for item in items for s in strings_of(item)]


def date_refs(case: dict) -> list[str]:
    """Every relative-date reference in a case, whole, malformed ones included (`{{date…}}`)."""
    return [m.group(0) for text in strings_of(case) for m in re.finditer(r"\{\{date[^}]*\}\}", text)]


def anchor_of(case: dict) -> datetime.date | None:
    """The case's `date_anchor` as a date: the run date at which its references write out the
    text a run saved before run dates were recorded was sent. None when it has none."""
    value = case.get(DATE_ANCHOR)
    try:
        return datetime.date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def dated(case: dict, on: datetime.date | None = None) -> dict:
    """The case with every `{{date…}}` reference written out for a run on `on` — prompt, pages,
    candidate_text, expectations, every string in it. With `on` None, the case's `date_anchor`
    stands in: a run saved before run dates were recorded was sent the text its anchor gives.

    Raises ClauseError for a reference the pattern cannot read, or for references with no date
    to write them for; a case with none comes back unchanged."""
    if not date_refs(case):
        return case
    day = on or anchor_of(case)
    if day is None:
        raise ClauseError(f"eval {case.get('id')}: dates relative to the run, and no run date or "
                          f"{DATE_ANCHOR} to write them for")

    def write(value):
        if isinstance(value, str):
            text = DATE_REF.sub(lambda m: written(shifted(day, m.group(1)), m.group(2)), value)
            if DATE_OPEN in text:
                raise ClauseError(f"eval {case.get('id')}: a date reference the loader cannot read "
                                  f"({text[text.index(DATE_OPEN):][:40]!r}) — the form is "
                                  f"{{{{date±Nd/m/y:{'|'.join(DATE_FORMS)}}}}}")
            return text
        if isinstance(value, dict):
            return {k: write(v) for k, v in value.items()}
        if isinstance(value, list):
            return [write(v) for v in value]
        return value
    return write(case)


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
