"""Operator mutations and faithful controls through the public gate."""

import pytest

from citebound import ClaimStatus, passages_from_texts, verify


@pytest.mark.parametrize(
    ("source", "wrong"),
    [
        ("Refunds are not permitted after 30 days.", "Refunds are permitted after 30 days."),
        ("Refunds are permitted after 30 days.", "Refunds are not permitted after 30 days."),
        ("The API does not support batch uploads.", "The API supports batch uploads."),
        ("Customer data is never shared externally.", "Customer data is shared externally."),
        ("The API cannot support batch uploads.", "The API supports batch uploads."),
        ("The API doesn't support batch uploads.", "The API supports batch uploads."),
        ("The API doesn’t support batch uploads.", "The API supports batch uploads."),
        (
            "Contractors must complete security training.",
            "Contractors may complete security training.",
        ),
        ("Claims shall be submitted in writing.", "Claims may be submitted in writing."),
        ("A manager is required to approve orders.", "A manager can approve orders."),
        ("Employees should complete training.", "Employees must complete training."),
        ("Some invoices require approval.", "All invoices require approval."),
        ("Backups are sometimes encrypted.", "Backups are always encrypted."),
        ("Requests above 500 USD need approval.", "Requests below 500 USD need approval."),
        (
            "Applicants need at least 5 years experience.",
            "Applicants need at most 5 years experience.",
        ),
        (
            "Accounts may register no more than 10 devices.",
            "Accounts may register no fewer than 10 devices.",
        ),
        (
            "The express fee is higher than the standard rate.",
            "The express fee is lower than the standard rate.",
        ),
        ("The policy takes effect after the audit.", "The policy takes effect before the audit."),
        (
            "Notice must be given prior to termination.",
            "Notice must be given following termination.",
        ),
    ],
)
def test_operator_mutation_is_rejected_and_source_is_kept(source: str, wrong: str) -> None:
    passages = passages_from_texts([source])
    rejected = verify(f"{wrong} [1]", passages, citation_style="numeric")
    assert not rejected.passed and not rejected.answer
    assert rejected.claims[0].status is ClaimStatus.STRIPPED
    assert verify(f"{source} [1]", passages, citation_style="numeric").passed


@pytest.mark.parametrize(
    ("source", "answer"),
    [
        ("Refunds are permitted. Exchanges are not permitted.", "Refunds are permitted."),
        ("Refunds are permitted but exchanges are not permitted.", "Refunds are permitted."),
        ("Refunds are permitted and exchanges are not permitted.", "Refunds are permitted."),
        ("Exchanges are not permitted. Refunds are permitted.", "Refunds are permitted."),
        (
            "Contractors must complete training. Employees may complete training.",
            "Employees may complete training.",
        ),
        ("The plan covers dental and vision care.", "The plan covers dental and vision care."),
        (
            "The plan covers not only dental but also vision care.",
            "The plan covers dental and vision care.",
        ),
        (
            "All employees are eligible for travel allowance.",
            "Some employees are eligible for travel allowance.",
        ),
        ("Backups are always encrypted.", "Backups are sometimes encrypted."),
        ("Contractors must complete training.", "Contractors are required to complete training."),
        ("Requests above 500 USD require approval.", "Requests above 500 USD need approval."),
        ("Refunds are permitted.", "No. Refunds are permitted."),
        (
            "Accounts may register no more than 10 devices.",
            "Accounts may register at most 10 devices.",
        ),
    ],
)
def test_faithful_controls(source: str, answer: str) -> None:
    assert verify(f"{answer} [1]", passages_from_texts([source]), citation_style="numeric").passed


def test_repair_checks_polarity_of_the_replacement() -> None:
    passages = passages_from_texts(
        [
            "Refunds are not permitted after 30 days.",
            "Refunds are permitted after 30 days.",
        ]
    )
    verdict = verify("Refunds are permitted after 30 days [1].", passages, citation_style="numeric")
    assert verdict.passed and verdict.cited_ids == ("p2",)
    assert verdict.claims[0].status is ClaimStatus.REPAIRED


def test_repair_does_not_reintroduce_a_rejected_passage() -> None:
    passages = passages_from_texts(
        [
            "Refunds are not permitted after 30 days.",
            "Refunds are never permitted after 30 days.",
        ]
    )
    verdict = verify("Refunds are permitted after 30 days [9].", passages, citation_style="numeric")
    assert not verdict.passed and verdict.repaired_citations == 0


def test_citation_group_cannot_pool_operators_from_unrelated_passages() -> None:
    passages = passages_from_texts(
        [
            "Refunds are not permitted after 30 days.",
            "Exchanges are permitted after 30 days.",
        ]
    )
    # The subject attribution problem remains outside this guard. Check the
    # contradictory passage cannot remain as supporting evidence even if a
    # lexically similar alternative is still accepted by the existing gate.
    verdict = verify(
        "Refunds are permitted after 30 days [1, 2].", passages, citation_style="numeric"
    )
    assert "p1" not in verdict.cited_ids


def test_unrelated_negative_sentence_cannot_hide_a_flip() -> None:
    source = "Refunds are not permitted after 30 days. Employees are permitted to travel."
    assert not verify(
        "Refunds are permitted after 30 days [1].",
        passages_from_texts([source]),
        citation_style="numeric",
    ).passed


def test_a_negative_heading_does_not_negate_the_body() -> None:
    from citebound import Passage

    source = Passage(text="Refunds are permitted.", section="Do not discard this policy")
    assert verify("Refunds are permitted [1].", [source], citation_style="numeric").passed


def test_another_threshold_cannot_supply_polarity() -> None:
    source = "Refunds are not permitted after 30 days. Refunds are permitted after 10 days."
    assert not verify(
        "Refunds are permitted after 30 days [1].",
        passages_from_texts([source]),
        citation_style="numeric",
    ).passed


@pytest.mark.parametrize("marker", ["1. ", "2) ", "- ", "* "])
def test_list_formatting_does_not_disable_the_guard(marker: str) -> None:
    source = passages_from_texts(["Refunds are not permitted after 30 days."])
    assert not verify(
        f"{marker}Refunds are permitted after 30 days [1].", source, citation_style="numeric"
    ).passed


@pytest.mark.parametrize(
    ("source", "claim"),
    [
        ("Do not forget to close the account.", "Close the account."),
        ("The filter prevents debris entering the pump.", "No debris enters the pump."),
        ("If the indicator is not lit, restart the machine.", "Restart the machine."),
        (
            "The notice will not appear when you disable alerts.",
            "Disabling alerts prevents the notice from appearing.",
        ),
    ],
)
def test_lexical_similarity_alone_does_not_establish_operator_scope(
    source: str, claim: str
) -> None:
    """Do not infer contradiction from a negative word in a different frame.

    This preserves the lexical gate's behavior; it does not certify that a
    summary retained every condition needed to act on the original instruction.
    """
    assert verify(f"{claim} [1]", passages_from_texts([source]), citation_style="numeric").passed


def test_polarity_cache_is_not_shared_between_requests() -> None:
    claim = "Refunds are permitted [1]."
    assert verify(
        claim, passages_from_texts(["Refunds are permitted."]), citation_style="numeric"
    ).passed
    assert not verify(
        claim, passages_from_texts(["Refunds are not permitted."]), citation_style="numeric"
    ).passed
