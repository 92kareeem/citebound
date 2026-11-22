"""A sentence that admits no answer is available is not a claim to verify.

Found on RAGTruth-derived data: 23 of 134 clean sentences were false refusals,
and some of those were not grounding failures at all - the model honestly
said it had nothing to add, and the gate punished it for saying so. This is
the fix, scoped narrowly on purpose: see the rationale in grounding.py's
module docstring and on ``_is_evidence_commentary`` for why a sentence naming
a specific absent topic is deliberately excluded. The four control tests
below are not synthetic - they are the real RAGTruth sentences, reworded with
stand-in topics, that an earlier and broader version of this pattern wrongly
accepted.
"""

from __future__ import annotations

from citebound import ClaimStatus, Passage, passages_from_texts, verify

REFUNDS = passages_from_texts(["Customers may request a refund within 30 days of purchase."])


def status(answer: str, passages: list[Passage] = REFUNDS, question: str = "") -> ClaimStatus:
    verdict = verify(answer, passages, question, citation_style="numeric")
    assert verdict.claims, "expected exactly one parsed claim"
    return verdict.claims[0].status


# --------------------------------------------------------- accepted outright


def test_a_blanket_inability_to_answer_is_accepted() -> None:
    assert status("(Unable to answer based on given passages) [1].") is ClaimStatus.SUPPORTED


def test_inability_to_answer_is_accepted_in_several_wordings() -> None:
    for wording in (
        "I am unable to answer this based on the given passages [1].",
        "I cannot answer this from the provided documents [1].",
        "Not able to answer using the available context [1].",
    ):
        assert status(wording) is ClaimStatus.SUPPORTED, wording


def test_a_bare_pointer_to_citations_is_accepted() -> None:
    for wording in (
        "(Passages 1, 2, and 3) [1].",
        "(Passage 1) [1].",
        "See passages 1 and 2 [1].",
    ):
        assert status(wording) is ClaimStatus.SUPPORTED, wording


def test_generic_insufficiency_with_no_named_topic_is_accepted() -> None:
    answer = (
        "Please note that the provided passages may not have all the necessary "
        "information to answer the question completely [1]."
    )
    assert status(answer) is ClaimStatus.SUPPORTED


def test_a_sole_bare_citation_answer_is_verified_not_refused() -> None:
    """Before this fix, a lone meta-sentence emptied every unit and the whole
    answer was refused (total == 0), even though nothing was actually wrong."""
    verdict = verify("(Passages 1, 2, and 3) [1].", REFUNDS, citation_style="numeric")
    assert verdict.ok
    assert verdict.passed
    assert verdict.claims[0].status is ClaimStatus.SUPPORTED


def test_accepted_sentences_keep_their_original_citation() -> None:
    verdict = verify(
        "Unable to answer from the given passages [1].", REFUNDS, citation_style="numeric"
    )
    assert verdict.cited_ids == ("p1",)
    assert verdict.claims[0].supported_by == ("p1",)


# --------------------------------------------------- never, even on a match


def test_a_matching_wording_is_never_accepted_with_a_number_present() -> None:
    """A figure is the one thing this gate always checks. Meta-language must
    never be a way to smuggle one past verification."""
    answer = "Unable to answer, but the fee is probably around $50 based on given passages [1]."
    assert status(answer) is ClaimStatus.STRIPPED


# ----------------------------------- naming a specific topic is NOT accepted


def test_naming_a_specific_absent_topic_is_not_accepted() -> None:
    """Reads the same as the accepted wordings, but this one is falsifiable:
    it claims the evidence is silent on a named thing, which this gate cannot
    verify and so must not wave through. (The quoted-in-docs RAGTruth example.)
    """
    answer = (
        "The passages do not provide detailed instructions on how to start "
        "a paw paw tree from seed [1]."
    )
    assert status(answer) is ClaimStatus.STRIPPED


def test_four_real_false_denials_are_still_caught() -> None:
    """RAGTruth's own labelled hallucinations: the model denies the evidence
    covers something it actually does. An earlier, broader version of this
    fix accepted all four unconditionally; each is a precision regression
    this test exists to catch if the pattern is ever widened again. The
    answers and passages are the real, public RAGTruth text, not paraphrased,
    so this test cannot be accidentally defeated by a synthetic passage that
    happens to be worded too conveniently (an earlier draft of this very test
    was).
    """
    duck = passages_from_texts(
        [
            "1 Roast duck in preheated oven for 1 hour. 2  Spoon 1/4 cup melted"
            " butter over bird, and continue cooking for 45 more minutes.",
            "Directions. Preheat the oven to 400 degrees F. Season the entire duck"
            " breast with Essence.",
            "Heat a cast iron skillet or other oven-safe skillet over medium heat."
            " Place the duck legs in the pan with the skin sides down.",
        ]
    )
    qualities = passages_from_texts(
        [
            "If you do good work and you're an effective manager, you shouldn't"
            " worry about dressing up your laurels. People will recognize the"
            " work that you do.",
            "The goal of a good manager is to achieve stellar results through"
            " inspiring, leading, and developing your team. Developing skills to"
            " become a good people manager is not easy.",
            "This is an excellent question to ask as you are getting promoted to"
            " manage others or have already been managing for awhile.",
        ]
    )
    components = passages_from_texts(
        [
            "Fuel Pump. The fuel pump has three functions: to deliver enough fuel"
            " to supply the requirements of an engine under all operating"
            " conditions, to maintain enough pressure in the line between the"
            " carburetor.",
            "The fuel sending unit assembly may be a combination of the electric"
            " fuel pump, the filter, the strainer, and the electronic device used"
            " to measure the amount of fuel in the tank via a float.",
            "With the whole unit you will get a new pressure regulator. Its a lot"
            " easier to change out.",
        ]
    )
    tuna = passages_from_texts(
        [
            "Salt and pepper to taste. 1  Heat your grill to a surface temperature"
            " of 400 degrees. 2  Rub oil on tuna steaks and season with salt and"
            " pepper.",
            "Pour half of your olive oil on the bottom of the aluminum foil. Chop"
            " up your green pepper into bite-size pieces.",
            "Broil the tuna for 3 minutes per side. After 3 minutes, flip the tuna"
            " steaks over to the other side and return to the broiler for an"
            " additional 3 minutes or until done.",
        ]
    )
    cases = [
        (
            "Note: The passages do not specify the size of the duck or the desired"
            " level of doneness, so the cooking time may need to be adjusted"
            " accordingly [1, 2, 3].",
            duck,
        ),
        (
            "The passages do not provide specific information on other important"
            " qualities such as adaptability, problem-solving skills,"
            " decision-making abilities, or conflict resolution strategies"
            " [1, 2, 3].",
            qualities,
        ),
        (
            "However, it's important to note that the passages don't provide a"
            " clear distinction between the two components, and they seem to be"
            " discussed interchangeably [1, 2, 3].",
            components,
        ),
        (
            "Note: The passages do not provide specific cooking times or"
            " temperatures, so it's important to check the tuna frequently during"
            " the broiling process [1, 2, 3].",
            tuna,
        ),
    ]
    for answer, passages in cases:
        assert status(answer, passages) is ClaimStatus.STRIPPED, answer
