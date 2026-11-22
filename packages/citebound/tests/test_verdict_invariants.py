"""Invalid configuration and empty output must never produce successful release."""

from dataclasses import replace
from typing import Any

import pytest

from citebound import RefusalReason, passages_from_texts, verify

PASSAGES = passages_from_texts(["Refunds take 30 days."])


def test_all_stripped_is_a_refusal_even_at_a_limit_of_one() -> None:
    verdict = verify(
        "Refunds take 90 days [1].", PASSAGES, citation_style="numeric", max_stripped_ratio=1
    )
    assert not verdict.ok and not verdict.passed and verdict.answer == ""
    assert verdict.refusal is RefusalReason.UNVERIFIABLE_ANSWER
    assert verdict.stripped_ratio == 1 and len(verdict.stripped) == 1
    assert verdict.safe_text() and "90" not in verdict.safe_text()
    output = verdict.to_dict()
    assert output["ok"] is False and output["passed"] is False
    assert output["safe_text"] == verdict.safe_text()


def test_limit_one_still_releases_a_nonempty_supported_subset() -> None:
    verdict = verify(
        "Refunds take 90 days [1]. Refunds take 60 days [1]. Refunds take 30 days [1].",
        PASSAGES,
        citation_style="numeric",
        max_stripped_ratio=1,
    )
    assert verdict.passed and verdict.stripped_ratio == 2 / 3
    assert verdict.answer == "Refunds take 30 days [1]."


def test_empty_public_verdict_cannot_offer_successful_safe_text() -> None:
    verdict = verify("Refunds take 30 days [1].", PASSAGES, citation_style="numeric")
    for text in ("", " \n\t"):
        empty = replace(verdict, answer=text)
        assert not empty.passed and empty.safe_text().strip()
        assert empty.to_dict()["passed"] is False


@pytest.mark.parametrize("name", ["max_stripped_ratio", "min_lexical_overlap"])
@pytest.mark.parametrize(
    "value", [-0.01, 1.01, float("nan"), float("inf"), float("-inf"), True, False, "0.5", None]
)
@pytest.mark.parametrize("answer", ["Refunds take 30 days [1].", "INSUFFICIENT_CONTEXT"])
def test_invalid_thresholds_fail_before_any_short_circuit(
    name: str, value: Any, answer: str
) -> None:
    with pytest.raises(ValueError, match=name):
        verify(answer, PASSAGES, citation_style="numeric", **{name: value})


@pytest.mark.parametrize("style", ["numbers", "", None])
def test_invalid_citation_style_is_not_silently_treated_as_tags(style: Any) -> None:
    with pytest.raises(ValueError, match="citation_style"):
        verify("Refunds take 30 days [chunk:p1].", PASSAGES, citation_style=style)


@pytest.mark.parametrize("threshold", [0, 0.0, 1, 1.0])
def test_valid_threshold_endpoints_still_accept_evidence(threshold: float) -> None:
    assert verify(
        "Refunds take 30 days [1].",
        PASSAGES,
        citation_style="numeric",
        max_stripped_ratio=threshold,
        min_lexical_overlap=threshold,
    ).passed
