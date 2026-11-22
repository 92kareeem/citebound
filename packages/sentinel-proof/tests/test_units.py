"""The unit guard: a figure must keep the unit its evidence quotes it with.

Every rejection here is paired with a control that must still be accepted.
A guard that refuses good answers is worse than the gap it closes, so the
controls carry more weight than the catches.
"""

from __future__ import annotations

import pytest

from sentinel_proof import passages_from_texts, verify
from sentinel_proof.units import conflicts, figures


def statuses(answer: str, texts: list[str], question: str = "") -> list[str]:
    verdict = verify(answer, passages_from_texts(texts), question, citation_style="numeric")
    return [claim.status.value for claim in verdict.claims]


# --------------------------------------------------------------- extraction


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Delivery takes 3 days.", {"3": {"day"}}),
        ("Implementation runs 12 weeks.", {"12": {"week"}}),
        ("Allow 3 business days.", {"3": {"day"}}),
        ("Allow 30 calendar days.", {"30": {"day"}}),
        ("The fee is 500 USD.", {"500": {"usd"}}),
        ("The fee is $500.", {"500": {"usd"}}),
        ("The fee is USD 500.", {"500": {"usd"}}),
        ("The rate is 4.5%.", {"4.5": {"percent"}}),
        ("The rate is 4.5 percent.", {"4.5": {"percent"}}),
        ("The fee is 1,200 USD.", {"1200": {"usd"}}),
        ("Storage is 50 GB.", {"50": {"gb"}}),
    ],
)
def test_a_figure_is_bound_to_the_unit_beside_it(text: str, expected: dict) -> None:
    assert {k: set(v) for k, v in figures(text).items()} == expected


@pytest.mark.parametrize(
    "text",
    [
        "The team has 12 people.",  # 'people' is not in the closed vocabulary
        "Clause 7 applies.",  # a reference, not a quantity
        "The plan allows 100 seats.",  # counting nouns are left to a subject check
        "Revenue grew in 2025.",  # a bare year carries no unit
    ],
)
def test_a_figure_with_no_unit_beside_it_is_left_alone(text: str) -> None:
    assert figures(text) == {}


def test_a_figure_in_a_range_carries_no_unit_of_its_own() -> None:
    """ "3 to 5 days" binds only 5. Rejecting a claim about 3 would be guesswork."""
    assert {k: set(v) for k, v in figures("Delivery takes 3 to 5 days.").items()} == {"5": {"day"}}


def test_punctuation_stops_a_figure_reaching_the_next_unit() -> None:
    assert figures("Choose 3, then wait days.") == {}


def test_the_next_figure_stops_the_lookahead() -> None:
    bound = figures("Pick 3 5 days.")
    assert "3" not in bound and set(bound["5"]) == {"day"}


def test_one_figure_quoted_two_ways_keeps_both_units() -> None:
    bound = figures("The 30 day window costs 30 USD.")
    assert set(bound["30"]) == {"day", "usd"}


# ------------------------------------------------------------------ conflict


def test_conflict_needs_the_same_figure_under_another_unit() -> None:
    assert conflicts(figures("3 months"), figures("3 days")) is True
    assert conflicts(figures("3 days"), figures("3 days")) is False
    # The evidence never quantifies 3, so the unit guard has nothing to say.
    assert conflicts(figures("3 days"), figures("the policy covers 3")) is False
    assert conflicts(figures("3 days"), figures("5 days")) is False


def test_an_ambiguous_figure_is_not_a_conflict() -> None:
    assert conflicts(figures("a 30 day window"), figures("30 days or 30 USD")) is False


# --------------------------------------------------------------- end to end


@pytest.mark.parametrize(
    ("answer", "evidence"),
    [
        ("Delivery takes 3 months [1].", "Standard delivery takes 3 days."),
        ("Customers may cancel within 30 hours [1].", "Customers may cancel within 30 days."),
        ("The annual licence costs 500 EUR [1].", "The annual licence costs 500 USD."),
        ("Implementation finishes within 12 months [1].", "Implementation finishes in 12 weeks."),
        ("The export is 50 MB [1].", "The export is 50 GB."),
    ],
)
def test_a_swapped_unit_is_stripped(answer: str, evidence: str) -> None:
    assert statuses(answer, [evidence]) == ["stripped"]


@pytest.mark.parametrize(
    ("answer", "evidence"),
    [
        ("Standard delivery takes 3 days [1].", "Standard delivery takes 3 days."),
        ("Delivery takes 3 business days [1].", "Delivery takes 3 business days."),
        # The unit is spelled differently on each side but means the same.
        ("The rate is 4.5 percent [1].", "The rate is 4.5%."),
        ("The fee is 1200 USD [1].", "The fee is 1,200 USD."),
        ("The fee is 500 USD [1].", "The fee is $500."),
        # 3 carries no unit inside the range, so the guard must stay silent.
        ("Delivery can take 3 days [1].", "Delivery takes 3 to 5 days."),
        # A plural on one side only.
        ("The term is 1 year [1].", "The term is 1 years."),
    ],
)
def test_the_same_quantity_written_differently_is_kept(answer: str, evidence: str) -> None:
    assert statuses(answer, [evidence]) == ["supported"]


# The three below were real false refusals on RAGTruth QA answers before the
# extraction was corrected. They are the reason the vocabulary is closed and
# the reason a figure may carry more than one unit.


def test_a_rate_carries_both_its_currency_and_its_period() -> None:
    """ "$1,720 per year" is a sum of money and a rate; one unit is not enough."""
    assert set(figures("$1,720 per year")["1720"]) == {"usd", "year"}
    answer = "The average cost is $1,720 per year [1]."
    assert statuses(answer, ["The average premium is $1,720 for a 55 year old."]) == ["supported"]


def test_pound_is_not_read_as_a_currency() -> None:
    """ "$1.98 per pound" and "44 pounds" are mass; "40 pounds" could be either."""
    assert figures("The ham is $1.98 per pound.")["1.98"] == frozenset({"usd"})
    answer = "The largest wallabies weigh up to 44 pounds [1]."
    assert statuses(answer, ["Large wallabies weigh up to 44 pounds."]) == ["supported"]


def test_a_following_amount_does_not_lend_its_currency_to_the_figure_before_it() -> None:
    """In "aged 55 is $1,720", the 55 is an age, not a sum of money."""
    assert "55" not in figures("For a person aged 55 is $1,720 per year.")


def test_a_second_figure_without_a_unit_does_not_block_the_first() -> None:
    answer = "Refunds take 3 days and need 2 approvals [1]."
    evidence = "Refunds take 3 days and need 2 approvals."
    assert statuses(answer, [evidence]) == ["supported"]


def test_repair_cannot_land_on_a_passage_that_swaps_the_unit() -> None:
    """The figure matches, so without the guard the wrong passage looks right."""
    passages = ["Refunds are processed within 2 weeks.", "Delivery takes 3 days."]
    assert statuses("Delivery takes 3 months [2].", passages) == ["stripped"]
    # The same claim with the unit kept is still repaired onto the right passage.
    assert statuses("Delivery takes 3 days [1].", passages) == ["repaired"]


def test_a_matching_unit_on_another_subject_still_captures_the_repair() -> None:
    """A known gap, recorded rather than hidden.

    The guard compares figures and units, not subjects. "Setup takes 3 months"
    quotes 3 as months, so it satisfies this guard and the lexical check, and
    the claim is repaired onto a sentence about a different thing. Closing this
    needs a check that can read the subject of a sentence; see the `attribute`
    class of the benchmark.
    """
    passages = ["Setup takes 3 months.", "Delivery takes 3 days."]
    assert statuses("Delivery takes 3 months [2].", passages) == ["repaired"]


def test_a_unit_swap_is_not_reported_as_a_missing_figure() -> None:
    """3 is in the evidence; what is wrong is the unit, so do not claim otherwise."""
    verdict = verify(
        "Delivery takes 3 months [1].",
        passages_from_texts(["Standard delivery takes 3 days."]),
        citation_style="numeric",
    )
    assert verdict.claims[0].unsupported_numbers == ()
