"""Core value types shared across airlock."""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


class Effect(enum.StrEnum):
    """What a tool does to the world. Policy is written against effects, not tool names."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    EGRESS = "egress"
    SPEND = "spend"


class ArgRole(enum.StrEnum):
    """What an argument means. Scope and provenance checks dispatch on roles."""

    PATH = "path"
    URL = "url"
    RECIPIENT = "recipient"
    PAYEE = "payee"
    AMOUNT = "amount"
    COMMAND = "command"
    CONTENT = "content"


class Verdict(enum.IntEnum):
    """Ordered by severity, so combining findings is ``max()``."""

    ALLOW = 0
    ESCALATE = 1
    DENY = 2
    HALT = 3

    @classmethod
    def parse(cls, value: str) -> Verdict:
        try:
            return cls[value.strip().upper()]
        except KeyError:
            allowed = ", ".join(v.name.lower() for v in cls)
            raise ValueError(f"unknown verdict {value!r} (expected one of: {allowed})") from None

    def __str__(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class ToolSpec:
    """Declared semantics of a tool. The gateway trusts this declaration, so keep it accurate."""

    name: str
    effects: frozenset[Effect]
    args: Mapping[str, ArgRole]
    irreversible: bool = False
    trusted_output: bool = False
    description: str = ""

    @property
    def consequential(self) -> bool:
        """True if the tool can change anything beyond reading."""
        return bool(self.effects - {Effect.READ})

    def args_with(self, *roles: ArgRole) -> list[str]:
        return [name for name, role in self.args.items() if role in roles]


@dataclass(frozen=True)
class Action:
    """A tool call proposed by the agent, before it runs."""

    tool: str
    args: Mapping[str, Any] = field(default_factory=dict)

    def describe(self) -> str:
        rendered = ", ".join(f"{k}={v!r}" for k, v in self.args.items())
        return f"{self.tool}({rendered})"


@dataclass(frozen=True)
class Finding:
    """One check's opinion about one action."""

    check: str
    verdict: Verdict
    message: str

    def __str__(self) -> str:
        return f"[{self.verdict}] {self.check}: {self.message}"


@dataclass(frozen=True)
class Review:
    """A reviewer's answer to an escalation."""

    approved: bool
    reviewer: str
    note: str = ""


@dataclass(frozen=True)
class Decision:
    """The gateway's final answer for one proposed action."""

    step: int
    action: Action
    verdict: Verdict
    findings: tuple[Finding, ...] = ()
    review: Review | None = None

    @property
    def allowed(self) -> bool:
        return self.verdict is Verdict.ALLOW

    @property
    def escalated(self) -> bool:
        return self.review is not None

    def explain(self) -> str:
        lines = [f"step {self.step}: {self.action.describe()} -> {self.verdict}"]
        lines.extend(f"  {f}" for f in self.findings)
        if self.review is not None:
            outcome = "approved" if self.review.approved else "rejected"
            note = f" ({self.review.note})" if self.review.note else ""
            lines.append(f"  review: {outcome} by {self.review.reviewer}{note}")
        return "\n".join(lines)
