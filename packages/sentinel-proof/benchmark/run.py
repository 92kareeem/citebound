"""Score a grounding gate against the adversarial case set.

    python benchmark/run.py                 # score and write report.md
    python benchmark/run.py --check         # also fail if a class got worse
    python benchmark/run.py --update-baseline

Most cases are contrastive pairs: a claim to reject and a faithful claim to
keep. The dataset also includes evidence-change and citation-repair controls;
see README.md for label and scoring limitations. A system that rejects
everything scores zero pairs. Pair accuracy is the headline number; a
false-accept rate on its own can always be bought with false refusals.

The case file is plain JSONL so that another tool can be scored on the same
inputs. See README.md for the schema.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from sentinel_proof import __version__, passages_from_texts, verify  # noqa: E402

# Every case set keeps the same four file names, so one scorer serves the
# hand-written set here and the set derived from RAGTruth in derived/.
CASES_NAME = "cases.jsonl"
BASELINE_NAME = "baseline.json"
CASE_BASELINE_NAME = "case-baseline.json"
REPORT_NAME = "report.md"
SCORER = "first-claim-status-v1"

KEPT = {"supported", "repaired"}
COUNTERS = ("reject", "keep", "false_accept", "false_refuse", "pairs", "pairs_ok")


def load(cases_path: Path) -> list[dict]:
    with cases_path.open(encoding="utf-8") as fh:
        cases = [json.loads(line) for line in fh if line.strip()]
    validate_cases(cases)
    return cases


def validate_cases(cases: list[dict]) -> None:
    """Fail before scoring when identities, labels or pair membership are ambiguous."""
    if not cases:
        raise ValueError("case set must not be empty")
    by_id = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("each case must be an object")
        for field in ("id", "pair", "class", "answer", "why"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                raise ValueError(f"case requires a nonempty string: {field}")
        cid = case["id"]
        if cid in by_id:
            raise ValueError(f"duplicate case id: {cid}")
        if case.get("expect") not in ("keep", "reject"):
            raise ValueError(f"{cid}: expect must be keep or reject")
        passages = case.get("passages")
        if not isinstance(passages, list) or not all(isinstance(p, str) for p in passages):
            raise ValueError(f"{cid}: passages must be a list of strings")
        if not isinstance(case.get("question", ""), str):
            raise ValueError(f"{cid}: question must be a string")
        if case.get("citation_style", "numeric") not in ("numeric", "tag"):
            raise ValueError(f"{cid}: unsupported citation_style")
        by_id[cid] = case
    for cid, case in by_id.items():
        twin = by_id.get(case["pair"])
        if twin is None or twin is case or twin["pair"] != cid:
            raise ValueError(f"{cid}: pair must reference a distinct reciprocal case")
        if twin["class"] != case["class"]:
            raise ValueError(f"{cid}: pair must belong to the same class")


def case_snapshot(cases: list[dict], results: list[dict]) -> dict:
    """Pin canonical case content separately from its measured outcome."""
    by_id = {row["id"]: row for row in results}
    return {
        "schema_version": 1,
        "scorer": SCORER,
        "cases": {
            case["id"]: {
                "sha256": hashlib.sha256(
                    json.dumps(
                        case, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                    ).encode("utf-8")
                ).hexdigest(),
                "correct": by_id[case["id"]]["correct"],
            }
            for case in cases
        },
    }


def case_regressions(old: dict, current: dict) -> list[str]:
    """Improvements cannot cancel a previously correct case becoming wrong."""
    if (
        not isinstance(old, dict)
        or old.get("schema_version") != 1
        or old.get("scorer") != SCORER
        or not isinstance(old.get("cases"), dict)
        or not old["cases"]
    ):
        return ["invalid or incompatible case baseline; review before updating"]
    problems = []
    previous = old["cases"]
    measured = current["cases"]
    for cid in sorted(previous.keys() - measured.keys()):
        problems.append(f"{cid}: case removed")
    for cid in sorted(measured.keys() - previous.keys()):
        problems.append(f"{cid}: new case requires a reviewed baseline update")
    for cid in sorted(previous.keys() & measured.keys()):
        want, got = previous[cid], measured[cid]
        if (
            not isinstance(want, dict)
            or type(want.get("correct")) is not bool
            or not isinstance(want.get("sha256"), str)
            or len(want["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in want["sha256"])
        ):
            problems.append(f"{cid}: invalid case baseline entry")
            continue
        if want["sha256"] != got["sha256"]:
            problems.append(f"{cid}: case content changed; review inputs and labels")
        if want["correct"] and not got["correct"]:
            problems.append(f"{cid}: previously correct case now wrong")
    return problems


def run_case(case: dict) -> tuple[bool, str]:
    """Did the claim survive, and what status did it get?"""
    verdict = verify(
        case["answer"],
        passages_from_texts(case["passages"]),
        case.get("question", ""),
        citation_style=case.get("citation_style", "numeric"),
    )
    if not verdict.claims:
        return False, "no claim parsed"
    status = verdict.claims[0].status.value
    return status in KEPT, status


def score(cases: list[dict]) -> tuple[dict, list[dict]]:
    validate_cases(cases)
    per_class: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(COUNTERS, 0))
    results = []
    for case in cases:
        kept, status = run_case(case)
        wanted_keep = case["expect"] == "keep"
        correct = kept == wanted_keep
        row = {**case, "kept": kept, "status": status, "correct": correct}
        results.append(row)
        bucket = per_class[case["class"]]
        bucket["keep" if wanted_keep else "reject"] += 1
        if not correct:
            bucket["false_refuse" if wanted_keep else "false_accept"] += 1

    by_id = {r["id"]: r for r in results}
    seen: set[str] = set()
    for row in results:
        twin = by_id.get(row["pair"])
        if twin is None or row["id"] in seen:
            continue
        seen |= {row["id"], twin["id"]}
        bucket = per_class[row["class"]]
        bucket["pairs"] += 1
        bucket["pairs_ok"] += int(row["correct"] and twin["correct"])
    return dict(per_class), results


def totals(per_class: dict) -> dict:
    out = dict.fromkeys(COUNTERS, 0)
    for bucket in per_class.values():
        for k in out:
            out[k] += bucket[k]
    return out


def pct(part: int, whole: int) -> str:
    return "n/a" if not whole else f"{100 * part / whole:.0f}%"


def write_report(report_path: Path, per_class: dict, results: list[dict], total: dict) -> None:
    lines = [
        "# Grounding benchmark report",
        "",
        f"`sentinel-proof` source checkout (declared version {__version__}) "
        f"against {len(results)} cases "
        f"({total['pairs']} paired examples). Generated by `python benchmark/run.py` "
        f"on {date.today().isoformat()}.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Pair accuracy (both halves right) | **{pct(total['pairs_ok'], total['pairs'])}** "
        f"({total['pairs_ok']} of {total['pairs']}) |",
        f"| False accepts (wrong claim kept) | {total['false_accept']} of {total['reject']} "
        f"({pct(total['false_accept'], total['reject'])}) |",
        f"| False refusals (right claim dropped) | {total['false_refuse']} of {total['keep']} "
        f"({pct(total['false_refuse'], total['keep'])}) |",
        "",
        "## By class",
        "",
        "| Class | Pairs | Pairs right | False accepts | False refusals |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in sorted(per_class):
        b = per_class[name]
        lines.append(
            f"| {name} | {b['pairs']} | {b['pairs_ok']} | "
            f"{b['false_accept']} / {b['reject']} | {b['false_refuse']} / {b['keep']} |"
        )
    wrong = [r for r in results if not r["correct"]]
    lines += ["", "## Cases the gate gets wrong", ""]
    if not wrong:
        lines.append("None.")
    else:
        lines += ["| Case | Class | Wanted | Got | Why the case is here |", "|---|---|---|---|---|"]
        for r in wrong:
            kind = "false refusal" if r["expect"] == "keep" else "false accept"
            got = f"{r['status']} ({kind})"
            lines.append(f"| `{r['id']}` | {r['class']} | {r['expect']} | {got} | {r['why']} |")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="check class and case regressions")
    mode.add_argument("--update-baseline", action="store_true")
    ap.add_argument(
        "--dir",
        type=Path,
        default=HERE,
        help="directory holding the case set and its baselines (default: this one)",
    )
    args = ap.parse_args()

    directory = args.dir.resolve()
    cases_path = directory / CASES_NAME
    baseline_path = directory / BASELINE_NAME
    case_baseline_path = directory / CASE_BASELINE_NAME
    report_path = directory / REPORT_NAME

    try:
        cases = load(cases_path)
    except (ValueError, OSError) as exc:
        ap.error(str(exc))
    per_class, results = score(cases)
    total = totals(per_class)
    write_report(report_path, per_class, results, total)

    width = max(len(name) for name in per_class)
    print(f"{'class'.ljust(width)}  pairs  right  false accept  false refuse")
    for name in sorted(per_class):
        b = per_class[name]
        print(
            f"{name.ljust(width)}  {b['pairs']:>5}  {b['pairs_ok']:>5}  "
            f"{b['false_accept']:>12}  {b['false_refuse']:>12}"
        )
    print(
        f"\npair accuracy {total['pairs_ok']}/{total['pairs']} "
        f"({pct(total['pairs_ok'], total['pairs'])}) | "
        f"false accepts {total['false_accept']}/{total['reject']} | "
        f"false refusals {total['false_refuse']}/{total['keep']}"
    )
    print(f"report written to {report_path.relative_to(HERE.parent)}")

    snapshot = {
        name: {k: b[k] for k in ("false_accept", "false_refuse", "pairs_ok")}
        for name, b in per_class.items()
    }
    case_state = case_snapshot(cases, results)
    if args.update_baseline:
        baseline_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        case_baseline_path.write_text(
            json.dumps(case_state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"baselines updated: {baseline_path.name}, {case_baseline_path.name}")
        return 0

    if args.check:
        if not baseline_path.exists() or not case_baseline_path.exists():
            print("missing class or case baseline; review and run --update-baseline first")
            return 1
        try:
            old = json.loads(baseline_path.read_text(encoding="utf-8"))
            old_cases = json.loads(case_baseline_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            print(f"cannot read baselines: {exc}")
            return 1
        regressions = case_regressions(old_cases, case_state)
        for name, want in old.items():
            got = snapshot.get(name)
            if got is None:
                regressions.append(f"class {name} disappeared from the case set")
                continue
            if got["false_accept"] > want["false_accept"]:
                regressions.append(
                    f"{name}: false accepts {want['false_accept']} -> {got['false_accept']}"
                )
            if got["false_refuse"] > want["false_refuse"]:
                regressions.append(
                    f"{name}: false refusals {want['false_refuse']} -> {got['false_refuse']}"
                )
            if got["pairs_ok"] < want["pairs_ok"]:
                regressions.append(f"{name}: pairs right {want['pairs_ok']} -> {got['pairs_ok']}")
        if regressions:
            print("\nREGRESSION against benchmark baselines:")
            for line in regressions:
                print(f"  {line}")
            return 1
        print("no regression against class or case baselines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
