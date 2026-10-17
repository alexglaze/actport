"""Deterministic checks. Each returns findings; an empty list means "no objection".

Checks never raise on bad agent input: anything they cannot parse becomes a
DENY finding. (If a check does raise, the gateway fails closed anyway.)
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from .policy import Policy
from .provenance import Origin, Provenance
from .scope import (
    Scope,
    command_allowed,
    host_allowed,
    normalize_path,
    parse_amount,
    parse_command,
    path_matches,
    payee_allowed,
    recipient_allowed,
    url_host,
)
from .types import Action, ArgRole, Effect, Finding, ToolSpec, Verdict

_MODIFYING = frozenset({Effect.WRITE, Effect.DELETE, Effect.EXECUTE})


@dataclass
class Usage:
    """What a session has consumed so far. Only allowed actions count."""

    actions: int = 0
    per_tool: Counter[str] = field(default_factory=Counter)
    spend: float = 0.0


@dataclass(frozen=True)
class Context:
    policy: Policy
    scope: Scope
    spec: ToolSpec | None
    provenance: Provenance
    usage: Usage


Check = Callable[[Context, Action], list[Finding]]


def _values(value: Any) -> Iterator[Any]:
    """Arguments may be a single value or a list of them (e.g. several recipients)."""
    if isinstance(value, list | tuple):
        yield from value
    else:
        yield value


def _role_values(spec: ToolSpec, action: Action, *roles: ArgRole) -> Iterator[tuple[str, ArgRole, Any]]:
    for name in spec.args_with(*roles):
        if name in action.args:
            for value in _values(action.args[name]):
                yield name, spec.args[name], value


def registry(ctx: Context, action: Action) -> list[Finding]:
    if ctx.spec is None:
        return [Finding("registry", ctx.policy.unknown_tool, f"tool {action.tool!r} is not registered")]
    undeclared = sorted(set(action.args) - set(ctx.spec.args))
    return [
        Finding("registry", Verdict.DENY, f"argument {name!r} is not declared for {action.tool!r}")
        for name in undeclared
    ]


def protected(ctx: Context, action: Action) -> list[Finding]:
    """The agent may never modify its own oversight: policy, audit log, approval channel."""
    spec = ctx.spec
    if spec is None or not (spec.effects & _MODIFYING) or not ctx.scope.protected_paths:
        return []
    candidates: list[tuple[str, str]] = []
    for name, _, value in _role_values(spec, action, ArgRole.PATH):
        if isinstance(value, str):
            candidates.append((name, value))
    for name, _, value in _role_values(spec, action, ArgRole.COMMAND):
        try:
            candidates += [(name, token) for token in parse_command(value)[1:]]
        except ValueError:
            continue  # the scope check reports unparseable commands
    findings = []
    for name, raw in candidates:
        try:
            path = normalize_path(raw, ctx.scope.cwd)
        except ValueError:
            continue
        hit = path_matches(path, ctx.scope.protected_paths)
        if hit is not None:
            findings.append(
                Finding(
                    "protected",
                    Verdict.HALT,
                    f"{name}={raw!r} touches protected path {hit!r}; modifying oversight ends the session",
                )
            )
    return findings


def scope(ctx: Context, action: Action) -> list[Finding]:
    spec = ctx.spec
    if spec is None:
        return []
    s = ctx.scope
    findings: list[Finding] = []

    def deny(message: str) -> None:
        findings.append(Finding("scope", Verdict.DENY, message))

    writes = bool(spec.effects & {Effect.WRITE, Effect.DELETE})
    for name, role, value in _role_values(spec, action, *ArgRole):
        if role is ArgRole.PATH:
            try:
                path = normalize_path(value, s.cwd)
            except ValueError as exc:
                deny(f"{name}: {exc}")
                continue
            allowed, kind = (s.write_paths, "write") if writes else (s.read_paths, "read")
            if path_matches(path, allowed) is None:
                deny(f"{name}={value!r} resolves to {path!r}, outside {kind} scope")
        elif role is ArgRole.URL:
            try:
                host = url_host(value)
            except ValueError as exc:
                deny(f"{name}: {exc}")
                continue
            if not host_allowed(host, s.domains):
                deny(f"{name}: host {host!r} is not in scope")
        elif role is ArgRole.RECIPIENT:
            if not recipient_allowed(value, s):
                deny(f"{name}: recipient {value!r} is not in scope")
        elif role is ArgRole.PAYEE:
            if not payee_allowed(value, s):
                deny(f"{name}: payee {value!r} is not in scope")
        elif role is ArgRole.AMOUNT:
            try:
                parse_amount(value)
            except ValueError as exc:
                deny(f"{name}: {exc}")
        elif role is ArgRole.COMMAND:
            try:
                parse_command(value)
            except ValueError as exc:
                deny(f"{name}: {exc}")
                continue
            if not command_allowed(value, s):
                deny(f"{name}: program {parse_command(value)[0]!r} is not in scope")
    return findings


def provenance(ctx: Context, action: Action) -> list[Finding]:
    """Flag control arguments copied from untrusted content rather than from the task."""
    spec = ctx.spec
    if spec is None or not spec.consequential:
        return []
    findings = []
    for name, _, value in _role_values(spec, action, *ctx.policy.provenance_roles):
        attribution = ctx.provenance.attribute(value)
        if attribution.origin is Origin.UNTRUSTED:
            sources = ", ".join(attribution.sources)
            findings.append(
                Finding(
                    "provenance",
                    ctx.policy.provenance,
                    f"{name}={value!r} appears in untrusted content ({sources}) but not in the task",
                )
            )
    return findings


def irreversible(ctx: Context, action: Action) -> list[Finding]:
    if ctx.spec is None or not ctx.spec.irreversible:
        return []
    return [Finding("irreversible", ctx.policy.irreversible, f"{action.tool!r} cannot be undone")]


def budget(ctx: Context, action: Action) -> list[Finding]:
    spec = ctx.spec
    if spec is None:
        return []
    b = ctx.policy.budget
    u = ctx.usage
    findings = []
    if b.max_actions is not None and u.actions >= b.max_actions:
        findings.append(Finding("budget", Verdict.DENY, f"session action limit ({b.max_actions}) reached"))
    limit = b.max_calls_per_tool.get(action.tool)
    if limit is not None and u.per_tool[action.tool] >= limit:
        findings.append(Finding("budget", Verdict.DENY, f"{action.tool!r} call limit ({limit}) reached"))
    if Effect.SPEND in spec.effects and b.max_spend is not None:
        amount = 0.0
        for _, _, value in _role_values(spec, action, ArgRole.AMOUNT):
            try:
                amount += parse_amount(value)
            except ValueError:
                continue  # the scope check reports malformed amounts
        if u.spend + amount > b.max_spend:
            findings.append(
                Finding(
                    "budget",
                    Verdict.DENY,
                    f"spend {amount:g} would bring the session to {u.spend + amount:g}, "
                    f"over the limit of {b.max_spend:g}",
                )
            )
    return findings


def spend_of(spec: ToolSpec, action: Action) -> float:
    if Effect.SPEND not in spec.effects:
        return 0.0
    total = 0.0
    for _, _, value in _role_values(spec, action, ArgRole.AMOUNT):
        total += parse_amount(value)
    return total


DEFAULT_CHECKS: tuple[Check, ...] = (registry, protected, scope, provenance, irreversible, budget)
