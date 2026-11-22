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
    monkeypatch.setattr(runner, "HERE", tmp_path)
    case_file = tmp_path / runner.CASES_NAME
    baseline = tmp_path / runner.BASELINE_NAME
    case_file.write_text("\n".join(json.dumps(c) for c in cases), encoding="utf-8")
    outcomes = {"good": (True, "supported"), "bad": (True, "supported")}
    monkeypatch.setattr(runner, "run_case", lambda case: outcomes[case["id"]])
    monkeypatch.setattr("sys.argv", ["run.py", "--update-baseline", "--dir", str(tmp_path)])
    assert runner.main() == 0
    # Two same-label controls let a false refusal move without changing totals.
    # Pin their labels before constructing that scenario.
    cases[1]["expect"] = "keep"
    case_file.write_text("\n".join(json.dumps(c) for c in cases), encoding="utf-8")
    outcomes["bad"] = (False, "stripped")
    assert runner.main() == 0
    original_class_baseline = baseline.read_bytes()
    outcomes.update(good=(False, "stripped"), bad=(True, "supported"))
    monkeypatch.setattr("sys.argv", ["run.py", "--check", "--dir", str(tmp_path)])
    assert runner.main() == 1
    assert "good: previously correct case now wrong" in capsys.readouterr().out
    assert baseline.read_bytes() == original_class_baseline


def test_check_and_update_cannot_be_combined(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run.py", "--check", "--update-baseline"])
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 2


DERIVED = Path(__file__).resolve().parents[1] / "benchmark" / "derived" / "cases.jsonl"


def test_the_derived_set_is_valid_and_keeps_its_provenance():
    """Every derived case must be traceable to the upstream record it came from.

    Without the ids nobody can check that the pairing is honest, which is the
    whole reason this set exists beside the hand-written one.
    """
    cases = runner.load(DERIVED)
    runner.validate_cases(cases)
    assert len(cases) >= 100
    for case in cases:
        source = case["source"]
        assert source["dataset"] == "RAGTruth"
        # The held-out split must never leak into a set that gets tuned against.
        assert source["split"] == "train"
        assert source["response_id"] and source["source_id"]
        assert len(case["passages"]) >= 2
        assert case["class"].startswith("rt-")


def test_every_derived_pair_is_one_reject_and_one_keep():
    cases = runner.load(DERIVED)
    by_id = {case["id"]: case for case in cases}
    for case in cases:
        twin = by_id[case["pair"]]
        assert {case["expect"], twin["expect"]} == {"reject", "keep"}
        # Same evidence on both halves: the pair isolates the claim.
        assert case["passages"] == twin["passages"]
