#!/usr/bin/env python3
"""Compare two saved fixture sets, an arm and its control, module by module.

The quality check through Tuesday (m18) was scored by scripts written beside each
step, and its verified summary found what that cost: a rate view blind to checks
that record only failures, one defect counted as two checks, p-values on grader
verdicts that two graders of one run make dependent, re-cut quotes mixed with
quotes that are not the candidate's words, and grader cost no script split out.
This is the one scorer, in the repository, for any comparison of two sets that
`run_fixtures.py` saved — through Tuesday against the module alone, or any arm
against its control.

It reports and decides nothing: it applies no threshold, and a measurement's bar
names its thresholds before the measurement runs. Per module it reports:

- the graded pass rate over both graders' verdicts, and each expectation's runs
  passing (every grader PASS) over the runs graded on it;
- whether the two sets were graded like for like: the grader prompt versions and
  grader models each set's grade files record, and per expectation the sha256 its
  grade files record. An expectation whose prompt version or text differs between
  the sets, or within one, is flagged on its row and given no p-value;
- runs with fewer grade files than the most any run has, a missing grader read as
  one that returned nothing; runs with no checks file; and files that could not be
  read, each reported and none aborting the report;
- each automatic check's failing runs over the runs where it applied. A check
  applies in a run that recorded a finding for it and did not list it unchecked;
  a check that writes a finding only to fail (output_checks.FAILURE_ONLY) applies
  in every valid run that did not list it unchecked. A check output_checks does
  not name is read from the data: failure-only when no run in either set recorded
  a PASS for it;
- the same checks with each check family counted once per run, the families and
  why each is one defect stated once in evals/README.md ("Comparing two arms");
- quote failures split into re-cut quotes (output_checks.recut_kind) and the rest;
- nudged runs, harness-invalid runs, refused tool calls by tool and runs with a
  refused save (run_fixtures.refusals, read from the graded invocation);
- cost: each invocation's stream (its result event's total_cost_usd) and each
  grade file's model usage.

Every comparison of runs carries an exact two-sided Fisher p-value on runs, never
on verdicts. Harness-invalid runs are counted and left out of everything else.

    python evals/compare_arms.py m18/opus/tuesday m18/opus/alone
    python evals/compare_arms.py ARM CONTROL --checks-from RECHECK/tuesday RECHECK/alone
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import output_checks  # noqa: E402
import run_fixtures  # noqa: E402
from fixture_clauses import ClauseError, dated  # noqa: E402

MODULES = tuple(run_fixtures.SKILLS)
# A finding saved before check_quotes labelled re-cut quotes is read by the reason it has
# always written for exactly that case.
RECUT_REASON = "is not in the fit snapshot's evidence column"
NO_TABLE = ("the response has no accounting table", "the accounting table could not be read")
# The set claim snapshot_count and ledger_sentence each quote first in their reasons.
CLAIM_IN = {"snapshot_count": re.compile(r'^the snapshot\'s prose: "(.+?)" is '),
            "ledger_sentence": re.compile(r'^in the sentence after the ledger, "(.+?)" is ')}
GRADE_FILE = re.compile(r"\.grade-(\d+)\.json$")


# --- Reading a set ------------------------------------------------------------------

def fisher(a: int, n1: int, b: int, n2: int) -> float | None:
    """Exact two-sided p for a of n1 against b of n2: with both margins fixed, the chance of a
    table no likelier than the one observed. None when either side has no runs."""
    if not n1 or not n2:
        return None
    k, n = a + b, n1 + n2
    total = comb(n, k)

    def p(x: int) -> float:
        return comb(n1, x) * comb(n2, k - x) / total
    observed = p(a)
    return min(1.0, sum(p(x) for x in range(max(0, k - n2), min(k, n1) + 1) if p(x) <= observed * (1 + 1e-9)))


def stream_cost(path: Path) -> float | None:
    """A stream's cost from its last result event, or None when it has none."""
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if '"type":"result"' in line or '"type": "result"' in line:
            try:
                return float(json.loads(line).get("total_cost_usd") or 0.0)
            except (json.JSONDecodeError, TypeError, ValueError):
                return None
    return None


def module_of(stem: str) -> str | None:
    return next((m for m in sorted(MODULES, key=len, reverse=True) if stem.startswith(m + "-")), None)


def fixture_cases() -> dict[tuple[str, int], dict]:
    """Every repository fixture, by module and id, as the runner loads it."""
    return {(m, c["id"]): c for m in MODULES for c in run_fixtures.cases_for(m, [])}


def aimed_targets(case: dict | None, meta: dict) -> dict[int, int] | None:
    """How many research calls of the run were aimed at each declared target, by the attribution
    the accounting checks use (output_checks.aimed_calls), with the fixture written for the run's
    date; None when the fixture or the research record is missing."""
    if not case or not case.get("research") or meta.get("research_log") is None:
        return None
    try:
        case = dated(case, run_fixtures.run_date(meta))
    except ClauseError:
        return None
    aimed = output_checks.aimed_calls(case["research"], meta.get("mode") or "denied", meta["research_log"],
                                      case.get("prompt", ""))
    return {n: len(calls) for n, calls in aimed.items()}


def read_json(path: Path, unreadable: list[str]) -> dict | None:
    """A saved file's JSON, or None with its name added to `unreadable` when it cannot be read
    (truncated, say): one bad file is reported, never the end of the report."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        unreadable.append(path.name)
        return None
    if not isinstance(data, dict):
        unreadable.append(path.name)
        return None
    return data


def load(folder: Path, checks_from: Path | None = None, cases: dict | None = None) -> list[dict]:
    """One record per saved run of a set: its harness status, nudge, checks (from `checks_from`
    when given, a re-check of the same runs), every grader's verdicts by grader number with the
    prompt version, model and expectation hashes its grade file records, refusals, cost, the
    targets its research calls were aimed at, and the files of it that could not be read. A run
    whose meta.json cannot be read is a record with `meta_read` False and nothing else read."""
    cases = fixture_cases() if cases is None else cases
    runs = []
    for meta_path in sorted(folder.glob("*.meta.json")):
        unreadable: list[str] = []
        meta = read_json(meta_path, unreadable)
        stem = (meta or {}).get("stem") or meta_path.name[: -len(".meta.json")]
        if meta is None:
            runs.append({"stem": stem, "skill": module_of(stem), "meta_read": False, "unreadable": unreadable})
            continue
        skill = meta.get("skill") or module_of(stem)
        status, reasons = run_fixtures.harness_status(meta)
        invocations = meta.get("invocations") or []
        index = meta.get("graded_invocation")
        graded = invocations[index] if isinstance(index, int) and 0 <= index < len(invocations) else \
            (invocations[-1] if invocations else {})
        refused, save_refused = run_fixtures.refusals(graded) if graded else (None, None)
        check_path = (checks_from or folder) / f"{stem}.checks.json"
        checks = read_json(check_path, unreadable) if check_path.exists() else None
        grades, graded_by, grader_cost, numbers = {}, {}, 0.0, set()
        for grade_path in sorted(folder.glob(f"{stem}.grade-*.json")):
            number = GRADE_FILE.search(grade_path.name)
            if not number:
                continue
            numbers.add(int(number.group(1)))
            grade = read_json(grade_path, unreadable)
            if grade is None:
                continue
            grader_cost += sum((u or {}).get("costUSD") or 0.0 for u in (grade.get("model_usage") or {}).values()
                               if isinstance(u, dict))
            if grade.get("harness_invalid"):
                continue
            grades[int(number.group(1))] = {v["n"]: v["verdict"] for v in grade.get("verdicts") or []
                                            if isinstance(v, dict) and v.get("verdict") in ("PASS", "FAIL")}
            hashes = grade.get("expectation_sha256")
            graded_by[int(number.group(1))] = {
                "version": grade.get("grader_prompt_version"), "model": grade.get("grader_model"),
                "hashes": {int(n): h for n, h in hashes.items() if str(n).isdigit()} if isinstance(hashes, dict) else {}}
        costs = []
        for inv in invocations:
            room = Path(inv.get("room") or "").name
            found = [p for p in (folder / "streams" / f"{room}.jsonl", folder / "streams" / f"{room}.partial.jsonl")
                     if room and p.exists()]
            costs.append(stream_cost(found[0]) if found else None)
        case = cases.get((skill, meta.get("id")))
        runs.append({
            "stem": stem, "skill": skill, "id": meta.get("id"), "mode": meta.get("mode"), "meta_read": True,
            "valid": status == "ok", "reasons": reasons, "nudged": meta.get("triggered_unprompted") is False,
            "checks": None if checks is None else list(checks.get("checks") or []),
            "unchecked": [] if checks is None else list(checks.get("unchecked") or []),
            "grades": grades, "graded_by": graded_by, "grade_files": numbers, "grader_cost": grader_cost,
            "expectations": len(case.get("expectations") or []) if case else None,
            "run_cost": sum(c for c in costs if c is not None), "cost_unread": sum(c is None for c in costs),
            "refused": refused, "save_refused": save_refused, "unreadable": unreadable,
            "aimed": aimed_targets(case, meta)})
    return runs


def expect_graders(*sets: list[dict]) -> int:
    """How many graders every valid run is held to: the most grade files any run of either set
    has, since a meta does not record how many were asked for. Set on each run as `graders`."""
    runs = [r for rs in sets for r in rs if r.get("meta_read")]
    most = max((max(r["grade_files"]) for r in runs if r["grade_files"]), default=0)
    for r in runs:
        r["graders"] = most
    return most


# --- Families: one defect, counted once per run ------------------------------------------

def failing(run: dict) -> list[dict]:
    return [f for f in run["checks"] or [] if f.get("verdict") == "FAIL"]


def fold_slot(*names: str):
    def fold(run: dict, fails: list[dict]) -> set[int]:
        return {i for i, f in enumerate(fails) if f["check"] in names}
    return fold


def fold_unneeded_call(run: dict, fails: list[dict]) -> set[int]:
    """zero_calls, and the accept and skip_has_no_call rows of the targets its calls were aimed at."""
    zero = {i for i, f in enumerate(fails) if f["check"] == "zero_calls"}
    if not zero:
        return set()
    aimed = {str(n) for n, calls in (run["aimed"] or {}).items() if calls}
    return zero | {i for i, f in enumerate(fails)
                   if f["check"] in ("accept", "skip_has_no_call") and f.get("target") in aimed}


def fold_unrefused_unavailable(run: dict, fails: list[dict]) -> set[int]:
    """unavailable_has_refusal for a target, and that target's accept row."""
    rows = {f.get("target") for f in fails if f["check"] == "unavailable_has_refusal"}
    return {i for i, f in enumerate(fails)
            if f["check"] == "unavailable_has_refusal" or (f["check"] == "accept" and f.get("target") in rows)}


def fold_no_accounting(run: dict, fails: list[dict]) -> set[int]:
    """Every row failed for the table's absence, and beside that absence the tally line failed,
    missing or written off its fixed form: one accounting block, not written or written as prose."""
    rows = {i for i, f in enumerate(fails) if f["check"] == "row" and str(f.get("why", "")).startswith(NO_TABLE)}
    return rows | {i for i, f in enumerate(fails) if f["check"] == "tally"} if rows else set()


def fold_one_claim(run: dict, fails: list[dict]) -> set[int]:
    """snapshot_count and ledger_sentence failed on the same set claim: the sentence after the
    ledger is part of the snapshot's prose, so one claim was read by both."""
    claims: dict[str, dict[str, int]] = {}
    for i, f in enumerate(fails):
        pattern = CLAIM_IN.get(f["check"])
        if pattern and (m := pattern.match(str(f.get("why", "")))):
            claims.setdefault(m.group(1), {}).setdefault(f["check"], i)
    return {i for found in claims.values() if len(found) == len(CLAIM_IN) for i in found.values()}


# (name, member checks, the members whose applying makes the family apply, fold).
# evals/README.md ("Comparing two arms") states why each is one defect, with the overlaps the
# m18 runs showed.
FAMILIES = (
    ("hard-gates line", ("gates_line", "gates_form"), ("gates_line", "gates_form"),
     fold_slot("gates_line", "gates_form")),
    ("severity slot", ("severity", "severity_form"), ("severity", "severity_form"),
     fold_slot("severity", "severity_form")),
    ("a call where none belongs", ("zero_calls", "accept", "skip_has_no_call"), ("zero_calls",),
     fold_unneeded_call),
    ("canned unavailable, nothing refused", ("unavailable_has_refusal", "accept"), ("unavailable_has_refusal",),
     fold_unrefused_unavailable),
    ("no accounting table, nor its tally line", ("row", "tally"), ("row", "tally"), fold_no_accounting),
    ("one set claim, read twice", ("snapshot_count", "ledger_sentence"), ("snapshot_count", "ledger_sentence"),
     fold_one_claim),
)


def defects(run: dict) -> dict[str, int]:
    """The run's failures as units counted once: each family that absorbed any failing finding, and
    each check with a failing finding no family absorbed. Value: how many member checks failed."""
    fails = failing(run)
    absorbed: set[int] = set()
    out: dict[str, int] = {}
    for name, _, _, fold in FAMILIES:
        got = fold(run, fails) - absorbed
        if got:
            out[name] = len({fails[i]["check"] for i in got})
            absorbed |= got
    for i, f in enumerate(fails):
        if i not in absorbed:
            out.setdefault(f["check"], 1)
    return out


def recut_of(finding: dict) -> str | None:
    """A quote failure's re-cut kind: its `recut` field, or `unrecorded` for a finding saved before
    the field whose reason names the case; None for any other finding."""
    if finding.get("check") != "quotes" or finding.get("verdict") != "FAIL":
        return None
    if finding.get("recut"):
        return finding["recut"]
    return "unrecorded" if RECUT_REASON in str(finding.get("why", "")) else None


# --- Reporting ---------------------------------------------------------------------------

def pct(a: int, n: int) -> str:
    return f"{100 * a / n:.1f}%" if n else "n/a"


def pval(p: float | None) -> str:
    return "p n/a" if p is None else "p<0.001" if p < 0.001 else f"p={p:.3f}"


def ratio_row(label: str, a: tuple[int, int], b: tuple[int, int], width: int = 40, extra: str = "",
              compared: bool = True) -> str:
    """One row of counts, with its p-value; `compared` False prints none (p n/a)."""
    return (f"  {label:<{width}} {a[0]:>3}/{a[1]:<3}  {b[0]:>3}/{b[1]:<3}  "
            f"{pval(fisher(a[0], a[1], b[0], b[1]) if compared else None)}{extra}")


def check_names(runs: list[dict]) -> list[str]:
    return sorted({f["check"] for r in runs if r["valid"] for f in r["checks"] or []})


def failure_only(runs: list[dict]) -> set[str]:
    """The checks of these runs that write a finding only to fail, as output_checks declares them
    (FAILURE_ONLY); a check it does not name (one since renamed, say) is read from the data,
    failure-only when no valid run given recorded a PASS for it."""
    names = set(check_names(runs))
    unknown = names - output_checks.FAILURE_ONLY - output_checks.RECORDS_PASSES
    passed = {f["check"] for r in runs if r["valid"] for f in r["checks"] or [] if f.get("verdict") == "PASS"}
    return (names & output_checks.FAILURE_ONLY) | (unknown - passed)


def applies(run: dict, check: str, only_failures: set[str]) -> bool:
    if run["checks"] is None or check in run["unchecked"]:
        return False
    return check in only_failures or any(f["check"] == check for f in run["checks"])


def check_counts(runs: list[dict], check: str, only_failures: set[str]) -> tuple[int, int]:
    applied = [r for r in runs if r["valid"] and applies(r, check, only_failures)]
    return sum(any(f["check"] == check for f in failing(r)) for r in applied), len(applied)


def unit_counts(runs: list[dict], unit: str, via: tuple[str, ...], only_failures: set[str]) -> tuple[int, int, int]:
    """Runs failing a unit (a family or a check outside them), runs where it applied (any check in
    `via` applied), and runs where more than one member check failed inside the unit."""
    applied = [r for r in runs if r["valid"] and any(applies(r, m, only_failures) for m in via)]
    got = [defects(r).get(unit, 0) for r in applied]
    return sum(1 for g in got if g), len(applied), sum(1 for g in got if g > 1)


def expectation_states(run: dict) -> dict[int, str]:
    """Each expectation's state in one run: fail if any grader failed it, pass if every grader
    passed it, partial when some grader returned nothing for it. A grader whose file is missing
    or unreadable, of the `graders` every run is held to (expect_graders), returned nothing; a
    run with no grade file has every expectation its fixture lists partial."""
    numbers = {n for g in run["grades"].values() for n in g}
    if not numbers and run.get("graders") and run.get("expectations"):
        numbers = set(range(1, run["expectations"] + 1))
    out = {}
    for n in numbers:
        got = [run["grades"].get(g, {}).get(n) for g in range(1, max(run.get("graders") or 0, *run["grades"], 0) + 1)]
        out[n] = "fail" if "FAIL" in got else "pass" if got and all(v == "PASS" for v in got) else "partial"
    return out


def grading_of(runs: list[dict], fid, mode: str, n: int) -> tuple[set, set]:
    """The grader prompt versions and expectation hashes recorded by the grade files that gave a
    verdict on expectation n of fixture fid in this mode (None where a file records none)."""
    versions, hashes = set(), set()
    for r in runs:
        if r["id"] != fid or (r["mode"] or "") != mode:
            continue
        for g, info in r["graded_by"].items():
            if n in r["grades"].get(g, {}):
                versions.add(info["version"])
                hashes.add(info["hashes"].get(n))
    return versions, hashes


def named(values: set) -> str:
    return "/".join(sorted(str(v) if v is not None else "unrecorded" for v in values))


def unlike(arm: tuple[set, set], ctl: tuple[set, set]) -> str | None:
    """Why an expectation's verdicts in the two sets are not like for like, or None: a grader
    prompt version, or an expectation text (its hash), that differs between the sets or within
    one, or a text one side's files record and the other's do not. Nothing is compared, and
    nothing flagged, where one side gave no verdict on it."""
    (va, ha), (vc, hc) = arm, ctl
    if not va or not vc:
        return None
    if len(va | vc) > 1:
        return f"grader prompt version {named(va)} against {named(vc)}"
    if len(ha | hc) > 1:
        return "expectation text unrecorded on one side" if None in ha | hc else "expectation text differs"
    return None


def module_report(mod: str, arm: list[dict], ctl: list[dict], names: tuple[str, str]) -> list[str]:
    a_all = [r for r in arm if r["skill"] == mod]
    c_all = [r for r in ctl if r["skill"] == mod]
    if not a_all and not c_all:
        return []
    a = [r for r in a_all if r["valid"]]
    c = [r for r in c_all if r["valid"]]
    lines = [f"", f"== {mod}: {names[0]} {len(a_all)} runs, {names[1]} {len(c_all)} runs",
             f"  {'':<40} {names[0]:>7}  {names[1]:>7}"]
    lines.append(ratio_row("harness-invalid runs", (len(a_all) - len(a), len(a_all)), (len(c_all) - len(c), len(c_all))))
    for side, rs in ((names[0], a_all), (names[1], c_all)):
        why = sorted({"; ".join(r["reasons"])[:100] for r in rs if not r["valid"]})
        if why:
            lines.append(f"    {side} harness-invalid: " + " | ".join(why[:4]))
    lines.append(ratio_row("nudged runs", (sum(r["nudged"] for r in a), len(a)), (sum(r["nudged"] for r in c), len(c))))

    keys = sorted({(r["id"], r["mode"] or "", n) for r in a + c for n in expectation_states(r)},
                  key=lambda k: (k[0] if isinstance(k[0], int) else 0, k[1], k[2]))
    unlike_keys = {k: why for k in keys if (why := unlike(grading_of(a, *k), grading_of(c, *k)))}

    def verdicts(rs, only=None):
        vs = [v for r in rs for g in r["grades"].values() for n, v in g.items()
              if only is None or (r["id"], r["mode"] or "", n) in only]
        return sum(v == "PASS" for v in vs), len(vs)
    va, vc = verdicts(a), verdicts(c)
    diff = (100 * va[0] / va[1] - 100 * vc[0] / vc[1]) if va[1] and vc[1] else None
    lines.append(f"  graded pass rate, both graders' verdicts: {names[0]} {va[0]}/{va[1]} ({pct(*va)}), "
                 f"{names[1]} {vc[0]}/{vc[1]} ({pct(*vc)})"
                 + (f", difference {diff:+.1f} points (no p-value: two graders of one run are not independent)"
                    if diff is not None else ""))
    if unlike_keys:
        ua, uc = verdicts(a, unlike_keys), verdicts(c, unlike_keys)
        lines.append(f"    NOT LIKE FOR LIKE: {len(unlike_keys)} expectation(s), flagged below, carry {ua[1]} / {uc[1]} of "
                     f"those verdicts, graded under a different prompt version or expectation text in the two sets")
    for side, rs in ((names[0], a), (names[1], c)):
        short = [r for r in rs if r["grade_files"] and len(r["grade_files"]) < (r.get("graders") or 0)]
        none = [r for r in rs if not r["grade_files"] and r.get("graders")]
        bad = [r for r in rs if any(GRADE_FILE.search(f) for f in r["unreadable"])]
        if short or none or bad:
            lines.append(f"    {side}: of {len(rs)} valid runs, {len(short)} with fewer than {rs[0].get('graders')} grade "
                         f"files, {len(none)} with none, {len(bad)} with one unreadable; a missing grader returned "
                         f"nothing, so its expectations read partial"
                         + (f" ({', '.join(r['stem'] for r in (short + none + bad)[:4])})" if short or none or bad else ""))
        unchecked = [r for r in rs if r["checks"] is None]
        if unchecked:
            lines.append(f"    {side}: {len(unchecked)} of {len(rs)} valid runs have no readable checks file, and are in "
                         f"no check row ({', '.join(r['stem'] for r in unchecked[:4])})")

    def refusal_lines():
        out = []
        for side, rs in ((names[0], a), (names[1], c)):
            read = [r for r in rs if r["refused"] is not None]
            tools: dict[str, int] = {}
            for r in read:
                for tool, n in r["refused"].items():
                    tools[tool] = tools.get(tool, 0) + n
            out.append(f"    {side}: {sum(bool(r['refused']) for r in read)} of {len(read)} runs read had a refusal; "
                       f"by tool {dict(sorted(tools.items())) or '{}'}"
                       + (f"; {len(rs) - len(read)} ended before their result event, unread" if len(read) < len(rs) else ""))
        return out
    sa = [r for r in a if r["save_refused"] is not None]
    sc = [r for r in c if r["save_refused"] is not None]
    lines.append(ratio_row("runs with a save refused (reported)", (sum(r["save_refused"] for r in sa), len(sa)),
                           (sum(r["save_refused"] for r in sc), len(sc))))
    lines.append("  refused tool calls (graded invocation, reported):")
    lines += refusal_lines()

    def cost(rs):
        return sum(r["run_cost"] for r in rs), sum(r["grader_cost"] for r in rs), sum(r["cost_unread"] for r in rs)
    for side, rs in ((names[0], a_all), (names[1], c_all)):
        run_c, grade_c, unread = cost(rs)
        lines.append(f"  cost, {side}: runs ${run_c:,.2f}, graders ${grade_c:,.2f}"
                     + (f" ({unread} invocation stream(s) with no result event, uncounted)" if unread else ""))

    only = failure_only(a + c)
    lines.append("  automatic checks: failing runs / runs where the check applied")
    for check in check_names(a + c):
        lines.append(ratio_row(check + (" (records only failures)" if check in only else ""),
                               check_counts(a, check, only), check_counts(c, check, only)))
    lines.append("  each family counted once per run, then the failures outside every family "
                 "(failing runs / runs where it applied; [n / n]: runs with two or more members failing)")
    present = set(check_names(a + c))
    families = {name: (members, via) for name, members, via, _ in FAMILIES if present & set(via)}
    for unit in [*families, *sorted(present)]:
        members, via = families.get(unit, ((unit,), (unit,)))
        fa, na, ma = unit_counts(a, unit, via, only)
        fc, nc, mc = unit_counts(c, unit, via, only)
        if unit not in families and not (fa or fc):
            continue
        label = f"{unit} [{'+'.join(members)}]" if unit in families else unit
        lines.append(ratio_row(label, (fa, na), (fc, nc), 52, f"   [{ma} / {mc}]" if unit in families else ""))
    unknown = [r for r in a + c if any(f["check"] == "zero_calls" for f in failing(r)) and r["aimed"] is None]
    if unknown:
        lines.append(f"    ({len(unknown)} run(s) failing zero_calls with no research record or fixture to aim its "
                     f"calls by: zero_calls alone folded)")

    quote_runs = [r for r in a + c if any(f["check"] == "quotes" for f in r["checks"] or [])]
    if quote_runs:
        lines.append("  quote failures, re-cut quotes apart (runs)")

        def quotes(rs):
            kinds = [[recut_of(f) for f in failing(r) if f["check"] == "quotes"] for r in rs]
            applied = [k for r, k in zip(rs, kinds) if applies(r, "quotes", only)]
            return {"any quote failure": (sum(bool(k) for k in applied), len(applied)),
                    "only re-cut quotes": (sum(bool(k) and all(k) for k in applied), len(applied)),
                    "a quote failure that is not re-cut": (sum(any(x is None for x in k) for k in applied), len(applied)),
                    **{f"a re-cut quote, {kind}": (sum(kind in k for k in applied), len(applied))
                       for kind in (*output_checks.RECUT_KINDS, "unrecorded")}}
        qa, qc = quotes(a), quotes(c)
        for key in qa:
            if qa[key][0] or qc[key][0] or not key.startswith("a re-cut"):
                lines.append(ratio_row(key, qa[key], qc[key]))

    lines.append("  expectations: runs passing (every grader PASS) / runs graded on it")
    for fid, mode, n in keys:
        def tally(rs):
            states = [expectation_states(r).get(n) for r in rs if r["id"] == fid and (r["mode"] or "") == mode]
            return (sum(s == "pass" for s in states), sum(s in ("pass", "fail") for s in states),
                    sum(s == "partial" for s in states))
        ta, tc = tally(a), tally(c)
        partial = f"   ({ta[2]} / {tc[2]} partially graded)" if ta[2] or tc[2] else ""
        why = unlike_keys.get((fid, mode, n))
        lines.append(ratio_row(f"fixture {fid}{f' [{mode}]' if mode else ''} #{n}", ta[:2], tc[:2], 40,
                               partial + (f"   [not like for like: {why}]" if why else ""), compared=why is None))
    return lines


def tallied(values) -> str:
    counts: dict[str, int] = {}
    for v in values:
        key = str(v) if v is not None else "unrecorded"
        counts[key] = counts.get(key, 0) + 1
    return ", ".join(f"{k} ({n})" for k, n in sorted(counts.items())) or "none"


def headline(arm: list[dict], ctl: list[dict], names: tuple[str, str], paths: tuple[Path, Path],
             unread: tuple[list[dict], list[dict]] = ([], [])) -> list[str]:
    lines = [f"compare_arms: {names[0]} ({paths[0]}) against {names[1]} ({paths[1]})"]
    for side, rs, lost in zip(names, (arm, ctl), unread):
        run_c = sum(r["run_cost"] for r in rs)
        grade_c = sum(r["grader_cost"] for r in rs)
        lines.append(f"  {side}: {len(rs)} runs, {sum(not r['valid'] for r in rs)} harness-invalid, "
                     f"{sum(r['nudged'] for r in rs if r['valid'])} nudged, "
                     f"{sum(bool(r['save_refused']) for r in rs if r['valid'])} with a save refused; "
                     f"cost ${run_c + grade_c:,.2f} (runs ${run_c:,.2f}, graders ${grade_c:,.2f})")
        graded = [g for r in rs if r["valid"] for g in r["graded_by"].values()]
        lines.append(f"    graded under prompt version {tallied(g['version'] for g in graded)}; "
                     f"by {tallied(g['model'] for g in graded)}")
        files = [f for r in rs for f in r["unreadable"]] + [f for r in lost for f in r["unreadable"]]
        if files:
            lines.append(f"    {len(files)} file(s) could not be read" + (f", {len(lost)} of them a meta.json whose "
                         f"run is left out of everything" if lost else "") + f": {', '.join(files[:6])}")
    versions = [{g["version"] for r in rs if r["valid"] for g in r["graded_by"].values()} for rs in (arm, ctl)]
    if all(versions) and (len(versions[0] | versions[1]) > 1):
        lines.append(f"  NOT LIKE FOR LIKE: graded under prompt version {named(versions[0])} against "
                     f"{named(versions[1])}; each expectation so graded is flagged and given no p-value")
    most = max((r.get("graders") or 0 for r in arm + ctl), default=0)
    if most:
        lines.append(f"  each valid run is held to {most} grader(s), the most grade files any run of either set has")
    lines.append(f"  {'graded pass rate, both graders':<34} {names[0]:>18}  {names[1]:>18}  difference")
    for mod in MODULES:
        def rate(rs):
            vs = [v for r in rs if r["skill"] == mod and r["valid"] for g in r["grades"].values() for v in g.values()]
            return sum(v == "PASS" for v in vs), len(vs)
        ra, rc = rate(arm), rate(ctl)
        if not ra[1] and not rc[1]:
            continue
        diff = f"{100 * ra[0] / ra[1] - 100 * rc[0] / rc[1]:+.1f} points" if ra[1] and rc[1] else "n/a"
        lines.append(f"  {mod:<34} {pct(*ra):>7} ({ra[0]}/{ra[1]})  {pct(*rc):>7} ({rc[0]}/{rc[1]})  {diff}")
    return lines


def report(arm_dir: Path, ctl_dir: Path, checks_from: tuple[Path, Path] | None = None,
           cases: dict | None = None) -> str:
    """The whole comparison as text: the headline, then each module. `cases` stands in for the
    repository's fixtures, by module and id."""
    cases = fixture_cases() if cases is None else cases
    loaded = [load(arm_dir, checks_from[0] if checks_from else None, cases),
              load(ctl_dir, checks_from[1] if checks_from else None, cases)]
    arm, ctl = ([r for r in rs if r["meta_read"]] for rs in loaded)
    expect_graders(arm, ctl)
    names = (arm_dir.name, ctl_dir.name if ctl_dir.name != arm_dir.name else f"{ctl_dir.name} (control)")
    lines = headline(arm, ctl, names, (arm_dir, ctl_dir), tuple([r for r in rs if not r["meta_read"]] for rs in loaded))
    if checks_from:
        lines.append(f"  checks read from {checks_from[0]} and {checks_from[1]}")
    for mod in MODULES:
        lines += module_report(mod, arm, ctl, names)
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare an arm's saved fixture set with its control's.")
    ap.add_argument("arm", type=Path, help="the arm's --out folder")
    ap.add_argument("control", type=Path, help="the control's --out folder")
    ap.add_argument("--checks-from", type=Path, nargs=2, metavar=("ARM_CHECKS", "CONTROL_CHECKS"),
                    help="read each run's .checks.json from these folders instead: a re-check of the same runs")
    args = ap.parse_args()
    for folder in (args.arm, args.control, *(args.checks_from or ())):
        if not folder.is_dir():
            ap.error(f"{folder} is not a folder")
    sys.stdout.write(report(args.arm, args.control, tuple(args.checks_from) if args.checks_from else None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
