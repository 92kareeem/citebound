from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel_proof.cli import main

PASSAGES = [
    "Customers may request a refund within 30 days of purchase.",
    {
        "text": "Refund requests above 500 USD require manager approval.",
        "id": "approvals",
        "source": "policy.md",
    },
]


@pytest.fixture
def passages_file(tmp_path: Path) -> Path:
    p = tmp_path / "passages.json"
    p.write_text(json.dumps(PASSAGES), encoding="utf-8")
    return p


def test_verified_answer_exits_zero(
    passages_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    answer = tmp_path / "a.txt"
    answer.write_text(
        "Refunds are available within 30 days [1]. Above 500 USD you need approval [2]."
    )
    code = main(["check", "--answer", str(answer), "--passages", str(passages_file), "--numeric"])
    out = capsys.readouterr().out
    assert code == 0 and out.startswith("VERIFIED: 2/2")


def test_unverifiable_answer_exits_one_with_json(
    passages_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    answer = tmp_path / "a.txt"
    answer.write_text("Refunds are available within 60 days [1].")
    code = main(
        ["check", "--answer", str(answer), "--passages", str(passages_file), "--numeric", "--json"]
    )
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["ok"] is False and report["refusal"] == "UNVERIFIABLE_ANSWER"
    assert report["claims"][0]["status"] == "stripped"
    assert report["claims"][0]["unsupported_numbers"] == ["60"]
    assert "guess" in report["safe_text"]


def test_answer_can_come_from_stdin(
    passages_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io

    monkeypatch.setattr(
        "sys.stdin", io.StringIO("Approval is needed above 500 USD [chunk:approvals].")
    )
    assert main(["check", "--passages", str(passages_file)]) == 0
    assert "VERIFIED" in capsys.readouterr().out


@pytest.mark.parametrize("limit", ["nan", "inf", "-inf", "-0.1", "1.1"])
def test_invalid_limit_is_a_usage_error(
    limit: str,
    passages_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("Refunds are available within 30 days [1]."))
    with pytest.raises(SystemExit) as exc:
        main(["check", "--passages", str(passages_file), "--numeric", f"--max-stripped={limit}"])
    assert exc.value.code == 2
    output = capsys.readouterr()
    assert not output.out and "max_stripped_ratio" in output.err
    assert "Traceback" not in output.err


def test_no_surviving_claims_exit_one_at_the_most_permissive_limit(
    passages_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("Refunds take 90 days [1]."))
    code = main(["check", "--passages", str(passages_file), "--numeric", "--max-stripped=1"])
    output = capsys.readouterr().out
    assert code == 1 and output.startswith("NOT VERIFIED") and "limit 100%" in output
