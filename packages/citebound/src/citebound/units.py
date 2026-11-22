"""Bind a figure to the unit it is quoted with.

A set of numbers cannot tell "3 days" from "3 months": both contribute the
token ``3``, so the numeric check accepts either against the other. This module
records which units a passage quotes each figure with, so a claim that keeps
the figure and swaps the unit stops being supported by that passage.

Conservative in the same way as the polarity guard. A passage is rejected only
when it quotes the claim's figure with a *different* unit and never with the
claim's own. A figure the passage does not quantify at all is left to the
numeric check, so a range ("3 to 5 days", where 3 carries no unit of its own),
a spelled-out figure and any unit outside the closed vocabulary below can never
cause a refusal here.

The vocabulary is deliberately small and closed. Counting nouns are left out:
"100 seats" against "100 licences" is a question about the subject of the
sentence, not about units, and belongs to a check that can read subjects.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from .passages import Passage

# canonical -> the spellings that mean it. Single letters that collide with
# other conventions (m for million or metre, g for gram) are left out.
_UNIT_GROUPS: dict[str, tuple[str, ...]] = {
    "second": ("second", "seconds", "sec", "secs"),
    "minute": ("minute", "minutes", "min", "mins"),
    "hour": ("hour", "hours", "hr", "hrs"),
    "day": ("day", "days"),
    "week": ("week", "weeks"),
    "month": ("month", "months"),
    "quarter": ("quarter", "quarters"),
    "year": ("year", "years"),
    "usd": ("usd", "dollar", "dollars", "$"),
    "eur": ("eur", "euro", "euros", "€"),
    # "pound" alone is left out on purpose: it is a currency in "40 pounds
    # sterling" and a mass in "40 pounds of flour", and binding it either way
    # makes an honest sentence collide with its own evidence.
    "gbp": ("gbp", "£"),
    "inr": ("inr", "rupee", "rupees", "₹"),
    "jpy": ("jpy", "yen"),
    "percent": ("percent", "percentage", "pct", "%"),
    "byte": ("byte", "bytes"),
    "kb": ("kb", "kilobyte", "kilobytes"),
    "mb": ("mb", "megabyte", "megabytes"),
    "gb": ("gb", "gigabyte", "gigabytes"),
    "tb": ("tb", "terabyte", "terabytes"),
    "kilogram": ("kg", "kilogram", "kilograms"),
    "pound_mass": ("lb", "lbs"),
    "kilometre": ("km", "kilometre", "kilometres", "kilometer", "kilometers"),
    "mile": ("mile", "miles"),
}
_ALIASES: dict[str, str] = {
    spelling: canonical for canonical, group in _UNIT_GROUPS.items() for spelling in group
}
_CURRENCIES = frozenset({"usd", "eur", "gbp", "inr", "jpy"})
_CURRENCY_SYMBOLS = frozenset("$€£₹")

_SYMBOLS = "%$€£₹"
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
# Only spaces and tabs are skipped, so a unit never binds across a line break,
# and anything that is not a word or a unit symbol ends the search.
_NEXT = re.compile(rf"[ \t]*([A-Za-z]+|[{_SYMBOLS}])")
_PREVIOUS = re.compile(rf"([A-Za-z]+|[{_SYMBOLS}])[ \t]*$")
# "3 business days" and "30 calendar days" must still bind; two words is enough
# for the qualifiers that occur in practice, and short enough that the next
# figure's unit cannot be captured by the figure before it.
_LOOKAHEAD = 2
_BEHIND = 16

Bindings = Mapping[str, frozenset[str]]


def _normalise(number: str) -> str:
    """Match the numeric check: separators dropped, a trailing point ignored."""
    return number.replace(",", "").rstrip(".")


def figures(text: str) -> dict[str, frozenset[str]]:
    """Every figure in ``text``, mapped to the units it is quoted with.

    Only the few characters around each figure are examined, so the cost
    follows the number of figures rather than the length of the passage.
    """
    bound: dict[str, set[str]] = {}
    for match in _NUMBER.finditer(text):
        # Both ends, not the first that matches: "$1,720 per year" is a sum of
        # money AND a rate per year. Recording only one of them makes the same
        # quantity disagree with itself when the evidence words it differently.
        units = {
            unit
            for unit in (
                _unit_after(text, match.end()),
                _currency_before(text, match.start()),
            )
            if unit is not None
        }
        if units:
            bound.setdefault(_normalise(match.group()), set()).update(units)
    return {number: frozenset(units) for number, units in bound.items()}


def _unit_after(text: str, position: int) -> str | None:
    """The first unit within the lookahead, not crossing into another quantity."""
    for _ in range(_LOOKAHEAD):
        word = _NEXT.match(text, position)
        if word is None:
            return None
        token = word.group(1)
        # A currency symbol opens the next amount, as in "aged 55 is $1,720".
        if token in _CURRENCY_SYMBOLS:
            return None
        unit = _ALIASES.get(token.lower())
        if unit is not None:
            return unit
        position = word.end()
    return None


def _currency_before(text: str, position: int) -> str | None:
    """A currency written in front of its amount, as in "$500" or "USD 500"."""
    word = _PREVIOUS.search(text, max(0, position - _BEHIND), position)
    if word is None:
        return None
    unit = _ALIASES.get(word.group(1).lower())
    return unit if unit in _CURRENCIES else None


def conflicts(claim: Bindings, evidence: Bindings) -> bool:
    """Whether the evidence quotes one of the claim's figures with another unit."""
    for number, units in claim.items():
        quoted = evidence.get(number)
        if not units or not quoted:
            continue  # the passage does not quantify this figure: not our call
        if not units & quoted:
            return True
    return False


class UnitGuard:
    """Request-local evidence parsing; no retained document data across calls."""

    def __init__(self) -> None:
        self._evidence: dict[str, dict[str, frozenset[str]]] = {}

    def allows(self, claim: Bindings, passage: Passage) -> bool:
        if not claim:  # nothing quantified: never parse the passage for nothing
            return True
        if passage.id not in self._evidence:
            self._evidence[passage.id] = figures(passage.evidence)
        return not conflicts(claim, self._evidence[passage.id])
