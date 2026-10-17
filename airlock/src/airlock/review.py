"""Human (or simulated) review of escalated actions."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TextIO

from .types import Action, Finding, Review, ToolSpec


@dataclass(frozen=True)
class ReviewRequest:
    session_id: str
    task: str
    step: int
    action: Action
    spec: ToolSpec | None
    findings: tuple[Finding, ...]

    def render(self) -> str:
        lines = [
            f"Session {self.session_id}, step {self.step}",
            f"Task: {self.task}",
            f"Proposed: {self.action.describe()}",
        ]
        if self.spec is not None:
            effects = ", ".join(sorted(self.spec.effects))
            lines.append(f"Effects: {effects}" + (" (irreversible)" if self.spec.irreversible else ""))
        lines.append("Why this needs review:")
        lines.extend(f"  - {f}" for f in self.findings)
        return "\n".join(lines)


class Reviewer(Protocol):
    def review(self, request: ReviewRequest) -> Review: ...


class ApproveAll:
    """Approves everything. Models a rubber-stamping reviewer; useful to measure reliance on review."""

    def review(self, request: ReviewRequest) -> Review:
        return Review(approved=True, reviewer="approve-all")


class DenyAll:
    """Rejects everything. Models running with no human available."""

    def review(self, request: ReviewRequest) -> Review:
        return Review(approved=False, reviewer="deny-all", note="no reviewer available")


class CallbackReviewer:
    """Approves only when ``fn`` returns exactly ``True``; any other value is a rejection."""

    def __init__(self, fn: Callable[[ReviewRequest], bool], name: str = "callback") -> None:
        self._fn = fn
        self._name = name

    def review(self, request: ReviewRequest) -> Review:
        return Review(approved=self._fn(request) is True, reviewer=self._name)


class ConsoleReviewer:
    """Asks on a terminal. Anything other than an explicit yes is a no."""

    def __init__(self, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
        self._in = stdin or sys.stdin
        self._out = stdout or sys.stdout

    def review(self, request: ReviewRequest) -> Review:
        print(request.render(), file=self._out)
        print("Approve? [y/N] ", end="", file=self._out, flush=True)
        answer = self._in.readline().strip().lower()
        return Review(approved=answer in ("y", "yes"), reviewer="console")
