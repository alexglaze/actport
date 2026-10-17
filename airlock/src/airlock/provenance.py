"""Where did an argument value come from?

Authority to act comes from the principal (the person who gave the task),
never from data the agent happened to read. This module keeps two pools of
text, trusted (the principal's words, plus outputs of tools declared
trusted) and untrusted (every other tool output), and attributes a proposed
argument value to one of them by whole-value occurrence.

This is deliberately coarse. It only recognises values copied verbatim (up
to case and surrounding punctuation). A value the agent derived or
transformed from untrusted text is reported as NOVEL, not UNTRUSTED. That is
why provenance is one layer among several and never the only thing standing
between a value and a sink.

"Verbatim" means the value occurs as a whole token: the characters around it
must not continue it. Letters, digits, ``_``, ``@``, ``+`` and ``-`` always
continue a value, and so does ``.`` when another such character follows, so
``team@acme.example`` is not found inside ``finance-team@acme.example`` or
``team@acme.example.org``, but is found at the end of a sentence.
"""

from __future__ import annotations

import enum
import math
import re
from dataclasses import dataclass, field

_BEFORE = r"(?<![\w@+.-])"
_AFTER = r"(?![\w@+-]|\.[\w@+-])"
_NUMERIC_STRING = re.compile(r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?")
_NUMBER = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\w])|(?<![\w.])\d+(?:\.\d+)?(?![\w])")


class Origin(enum.StrEnum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    NOVEL = "novel"


@dataclass(frozen=True)
class Attribution:
    origin: Origin
    sources: tuple[str, ...] = ()


@dataclass
class _Text:
    source: str
    folded: str
    numbers: frozenset[float]


def _numbers(text: str) -> frozenset[float]:
    found = set()
    for match in _NUMBER.finditer(text):
        try:
            found.add(float(match.group().replace(",", "")))
        except ValueError:
            continue
    return frozenset(found)


@dataclass
class Provenance:
    """Ledger of the text seen in one session."""

    min_length: int = 3
    _trusted: list[_Text] = field(default_factory=list)
    _untrusted: list[_Text] = field(default_factory=list)

    def add_trusted(self, text: str, source: str) -> None:
        self._trusted.append(_Text(source, text.casefold(), _numbers(text)))

    def add_untrusted(self, text: str, source: str) -> None:
        self._untrusted.append(_Text(source, text.casefold(), _numbers(text)))

    def attribute(self, value: object) -> Attribution:
        """Attribute a single argument value.

        Numbers, and strings that are just a number (``"1,200"``, ``"$420.00"``),
        are compared numerically at any size. Other strings shorter than
        ``min_length`` are never attributed.
        """
        if isinstance(value, bool):
            return Attribution(Origin.NOVEL)
        if isinstance(value, int | float):
            return self._attribute_number(float(value))
        if not isinstance(value, str):
            return Attribution(Origin.NOVEL)
        numeric = _NUMERIC_STRING.fullmatch(value.strip())
        if numeric:
            return self._attribute_number(float(numeric.group(1).replace(",", "") + (numeric.group(2) or "")))
        needle = value.strip().casefold()
        if len(needle) < self.min_length:
            return Attribution(Origin.NOVEL)
        pattern = re.compile(_BEFORE + re.escape(needle) + _AFTER)
        if any(pattern.search(t.folded) for t in self._trusted):
            return Attribution(Origin.TRUSTED)
        sources = tuple(t.source for t in self._untrusted if pattern.search(t.folded))
        if sources:
            return Attribution(Origin.UNTRUSTED, sources)
        return Attribution(Origin.NOVEL)

    def _attribute_number(self, number: float) -> Attribution:
        if not math.isfinite(number):
            return Attribution(Origin.NOVEL)

        def seen(texts: list[_Text]) -> list[str]:
            return [t.source for t in texts if any(math.isclose(number, n) for n in t.numbers)]

        if seen(self._trusted):
            return Attribution(Origin.TRUSTED)
        sources = seen(self._untrusted)
        if sources:
            return Attribution(Origin.UNTRUSTED, tuple(sources))
        return Attribution(Origin.NOVEL)
