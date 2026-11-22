"""A class-level improvement must not hide a previously correct case regressing."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "benchmark_run", Path(__file__).resolve().parents[1] / "benchmark" / "run.py"
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@pytest.fixture
def cases():
    return [
        {
            "id": cid,
            "pair": pair,
            "class": "fabrication",
            "answer": answer,
            "expect": expect,
            "passages": ["Refunds take 30 days."],
            "why": "A refund figure must come from the cited policy.",
        }
        for cid, pair, answer, expect in (
            ("good", "bad", "Refunds take 30 days [1].", "keep"),
            ("bad", "good", "Refunds take 90 days [1].", "reject"),
        )
    ]


def snapshot(cases, good=True, bad=True):
    return runner.case_snapshot(
        cases, [{"id": "good", "correct": good}, {"id": "bad", "correct": bad}]
    )


def test_swapped_successes_cannot_cancel_each_other(cases):
    before = snapshot(cases, good=True, bad=False)
    after = snapshot(cases, good=False, bad=True)
    assert runner.case_regressions(before, after) == ["good: previously correct case now wrong"]


def test_improvements_and_unchanged_failures_are_allowed(cases):
    before = snapshot(cases, bad=False)
    assert runner.case_regressions(before, snapshot(cases)) == []
    assert runner.case_regressions(before, before) == []


@pytest.mark.parametrize("field", ["answer", "passages", "expect", "why", "question"])
def test_changed_case_content_requires_review_even_with_same_score(cases, field):
    before = snapshot(cases)
    cases[0][field] = ["New evidence"] if field == "passages" else "changed"
    assert "good: case content changed; review inputs and labels" in runner.case_regressions(
        before, snapshot(cases)
    )


def test_hashes_ignore_json_layout_key_order_and_case_order(cases):
    reordered = [dict(reversed(list(case.items()))) for case in reversed(cases)]
    assert snapshot(cases) == snapshot(json.loads(json.dumps(reordered, indent=4)))


def test_removing_or_adding_cases_requires_review(cases):
    before = snapshot(cases)
    after = deepcopy(before)
    after["cases"]["new"] = after["cases"].pop("good")
    assert runner.case_regressions(before, after) == [
        "good: case removed",
        "new: new case requires a reviewed baseline update",
    ]


@pytest.mark.parametrize("baseline", [None, {}, {"schema_version": 999}])
def test_invalid_baselines_fail_closed(cases, baseline):
    assert runner.case_regressions(baseline, snapshot(cases))


@pytest.mark.parametrize("entry", [{}, {"correct": "false", "sha256": "a" * 64}, None])
def test_invalid_case_entries_fail_closed(cases, entry):
    before = snapshot(cases)
    before["cases"]["good"] = entry
    assert runner.case_regressions(before, snapshot(cases)) == ["good: invalid case baseline entry"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "bad"),
        ("pair", "missing"),
        ("pair", "good"),
        ("class", "other"),
        ("expect", "accept"),
        ("passages", "not a list"),
        ("passages", [12]),
        ("question", None),
        ("citation_style", "other"),
        ("answer", ""),
    ],
)
def test_malformed_cases_fail_before_scoring(cases, field, value):
    cases[0][field] = value
    with pytest.raises(ValueError):
        runner.score(cases)


def test_nonreciprocal_pair_fails(cases):
    third = {**cases[0], "id": "third", "pair": "bad"}
    cases[1]["pair"] = "third"
    with pytest.raises(ValueError, match="reciprocal"):
        runner.validate_cases([*cases, third])


def test_empty_dataset_fails():
    with pytest.raises(ValueError, match="empty"):
        runner.score([])


def test_two_keep_repair_control_is_valid(cases):
    cases[1]["expect"] = "keep"
    runner.validate_cases(cases)


def test_cli_check_detects_case_regression_with_unchanged_class_totals(
    cases, monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(runner, "CASES", tmp_path / "cases.jsonl")
    monkeypatch.setattr(runner, "BASELINE", tmp_path / "baseline.json")
    monkeypatch.setattr(runner, "CASE_BASELINE", tmp_path / "case-baseline.json")
    monkeypatch.setattr(runner, "REPORT", tmp_path / "report.md")
    monkeypatch.setattr(runner, "HERE", tmp_path)
    runner.CASES.write_text("\n".join(json.dumps(c) for c in cases), encoding="utf-8")
    outcomes = {"good": (True, "supported"), "bad": (True, "supported")}
    monkeypatch.setattr(runner, "run_case", lambda case: outcomes[case["id"]])
    monkeypatch.setattr("sys.argv", ["run.py", "--update-baseline"])
    assert runner.main() == 0
    # Two same-label controls let a false refusal move without changing totals.
    # Pin their labels before constructing that scenario.
    cases[1]["expect"] = "keep"
    runner.CASES.write_text("\n".join(json.dumps(c) for c in cases), encoding="utf-8")
    outcomes["bad"] = (False, "stripped")
    assert runner.main() == 0
    original_class_baseline = runner.BASELINE.read_bytes()
    outcomes.update(good=(False, "stripped"), bad=(True, "supported"))
    monkeypatch.setattr("sys.argv", ["run.py", "--check"])
    assert runner.main() == 1
    assert "good: previously correct case now wrong" in capsys.readouterr().out
    assert runner.BASELINE.read_bytes() == original_class_baseline


def test_check_and_update_cannot_be_combined(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run.py", "--check", "--update-baseline"])
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 2
