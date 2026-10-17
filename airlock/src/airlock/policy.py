"""Policy: the tool registry, the scope ceiling, budgets, and how strict each check is."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from .scope import Scope
from .types import ArgRole, Effect, ToolSpec, Verdict

_E = TypeVar("_E", Effect, ArgRole)

DEFAULT_PROVENANCE_ROLES = frozenset(
    {ArgRole.PATH, ArgRole.RECIPIENT, ArgRole.PAYEE, ArgRole.AMOUNT, ArgRole.COMMAND}
)


class PolicyError(ValueError):
    """Raised for a malformed policy. The message names the offending key."""


@dataclass(frozen=True)
class Budget:
    """Hard limits for one session. ``None`` means unlimited."""

    max_actions: int | None = 100
    max_calls_per_tool: Mapping[str, int] = field(default_factory=dict)
    max_spend: float | None = 0.0


@dataclass(frozen=True)
class Policy:
    name: str
    tools: Mapping[str, ToolSpec]
    scope: Scope = field(default_factory=Scope)
    budget: Budget = field(default_factory=Budget)
    unknown_tool: Verdict = Verdict.DENY
    irreversible: Verdict = Verdict.ESCALATE
    provenance: Verdict = Verdict.ESCALATE
    provenance_roles: frozenset[ArgRole] = DEFAULT_PROVENANCE_ROLES
    max_denials: int | None = 3

    def lint(self) -> list[str]:
        """Warnings about settings that are legal but probably a mistake."""
        warnings: list[str] = []
        if self.unknown_tool is Verdict.ALLOW:
            warnings.append("policy.unknown_tool = allow: unregistered tools run unchecked")
        elif self.unknown_tool is Verdict.ESCALATE:
            warnings.append(
                "policy.unknown_tool = escalate: approved unregistered tools skip every effect-based check"
            )
        if self.irreversible is Verdict.ALLOW:
            warnings.append("checks.irreversible = allow: irreversible actions need no review")
        if self.provenance is Verdict.ALLOW:
            warnings.append("checks.provenance = allow: provenance is computed but never acted on")
        if self.max_denials is None:
            warnings.append("circuit_breaker.max_denials unset: a session is never halted")
        if not self.scope.protected_paths:
            warnings.append("scope.protected_paths is empty: the agent can edit its own policy and audit log")
        if self.budget.max_actions is None:
            warnings.append("budget.max_actions unset: a looping agent is never stopped")
        for spec in self.tools.values():
            if Effect.SPEND in spec.effects and not spec.args_with(ArgRole.AMOUNT):
                warnings.append(f"tools.{spec.name}: spends money but has no 'amount' argument")
            if Effect.SPEND in spec.effects and not spec.args_with(ArgRole.PAYEE):
                warnings.append(f"tools.{spec.name}: spends money but has no 'payee' argument")
            if Effect.EGRESS in spec.effects and not spec.args_with(ArgRole.URL, ArgRole.RECIPIENT):
                warnings.append(f"tools.{spec.name}: egress with no url/recipient argument cannot be scoped")
            if (spec.effects & {Effect.DELETE, Effect.SPEND}) and not spec.irreversible:
                warnings.append(f"tools.{spec.name}: deletes or spends but is not irreversible")
            if Effect.EXECUTE in spec.effects and not spec.args_with(ArgRole.COMMAND):
                warnings.append(f"tools.{spec.name}: executes but has no 'command' argument")
        unknown_budgeted = set(self.budget.max_calls_per_tool) - set(self.tools)
        for name in sorted(unknown_budgeted):
            warnings.append(f"budget.max_calls_per_tool.{name}: no such tool")
        return warnings


def load_policy(path: str | Path) -> Policy:
    with open(path, "rb") as fh:
        try:
            data = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise PolicyError(f"{path}: {exc}") from exc
    return policy_from_dict(data)


def policy_from_dict(data: Mapping[str, Any]) -> Policy:
    _only(data, {"policy", "scope", "budget", "checks", "circuit_breaker", "tools"}, "")
    meta = _table(data, "policy")
    _only(meta, {"name", "unknown_tool"}, "policy")
    checks = _table(data, "checks")
    _only(checks, {"irreversible", "provenance"}, "checks")
    prov = _table(checks, "provenance", "checks")
    _only(prov, {"verdict", "roles"}, "checks.provenance")
    breaker = _table(data, "circuit_breaker")
    _only(breaker, {"max_denials"}, "circuit_breaker")

    tools = {name: _tool(name, spec) for name, spec in _table(data, "tools").items()}
    if not tools:
        raise PolicyError("tools: a policy must register at least one tool")

    roles = prov.get("roles")
    return Policy(
        name=_str(meta.get("name", "unnamed"), "policy.name"),
        tools=tools,
        scope=_scope(_table(data, "scope")),
        budget=_budget(_table(data, "budget")),
        unknown_tool=_verdict(meta.get("unknown_tool", "deny"), "policy.unknown_tool"),
        irreversible=_verdict(checks.get("irreversible", "escalate"), "checks.irreversible"),
        provenance=_verdict(prov.get("verdict", "escalate"), "checks.provenance.verdict"),
        provenance_roles=(
            DEFAULT_PROVENANCE_ROLES
            if roles is None
            else frozenset(
                _enum(ArgRole, r, f"checks.provenance.roles[{i}]")
                for i, r in enumerate(_list(roles, "checks.provenance.roles"))
            )
        ),
        max_denials=_opt_int(breaker.get("max_denials", 3), "circuit_breaker.max_denials"),
    )


def _tool(name: str, raw: Any) -> ToolSpec:
    where = f"tools.{name}"
    if not isinstance(raw, Mapping):
        raise PolicyError(f"{where}: expected a table")
    _only(raw, {"effects", "args", "irreversible", "trusted_output", "description"}, where)
    effects = frozenset(
        _enum(Effect, e, f"{where}.effects[{i}]")
        for i, e in enumerate(_list(raw.get("effects", []), f"{where}.effects"))
    )
    if not effects:
        raise PolicyError(f"{where}.effects: declare at least one effect")
    args_raw = raw.get("args", {})
    if not isinstance(args_raw, Mapping):
        raise PolicyError(f"{where}.args: expected a table of argument -> role")
    args = {arg: _enum(ArgRole, role, f"{where}.args.{arg}") for arg, role in args_raw.items()}
    return ToolSpec(
        name=name,
        effects=effects,
        args=args,
        irreversible=_bool(raw.get("irreversible", False), f"{where}.irreversible"),
        trusted_output=_bool(raw.get("trusted_output", False), f"{where}.trusted_output"),
        description=_str(raw.get("description", ""), f"{where}.description"),
    )


def _scope(raw: Mapping[str, Any]) -> Scope:
    fields = {
        "read_paths",
        "write_paths",
        "protected_paths",
        "domains",
        "recipients",
        "recipient_domains",
        "payees",
        "commands",
    }
    _only(raw, fields | {"cwd"}, "scope")
    lists = {
        key: tuple(_str(v, f"scope.{key}[{i}]") for i, v in enumerate(_list(raw[key], f"scope.{key}")))
        for key in fields
        if key in raw
    }
    try:
        return Scope(cwd=_str(raw.get("cwd", "/"), "scope.cwd"), **lists)
    except ValueError as exc:
        raise PolicyError(f"scope.cwd: {exc}") from None


def _budget(raw: Mapping[str, Any]) -> Budget:
    _only(raw, {"max_actions", "max_calls_per_tool", "max_spend"}, "budget")
    per_tool = raw.get("max_calls_per_tool", {})
    if not isinstance(per_tool, Mapping):
        raise PolicyError("budget.max_calls_per_tool: expected a table of tool -> count")
    spend = raw.get("max_spend", 0.0)
    if spend is not None and (isinstance(spend, bool) or not isinstance(spend, int | float)):
        raise PolicyError("budget.max_spend: expected a number")
    if spend is not None and spend < 0:
        raise PolicyError("budget.max_spend: must be non-negative")
    return Budget(
        max_actions=_opt_int(raw.get("max_actions", 100), "budget.max_actions"),
        max_calls_per_tool={k: _int(v, f"budget.max_calls_per_tool.{k}") for k, v in per_tool.items()},
        max_spend=None if spend is None else float(spend),
    )


def _only(raw: Mapping[str, Any], allowed: set[str], where: str) -> None:
    extra = sorted(set(raw) - allowed)
    if extra:
        prefix = f"{where}." if where else ""
        raise PolicyError(f"{prefix}{extra[0]}: unknown key (typo?)")


def _table(raw: Mapping[str, Any], key: str, where: str = "") -> Mapping[str, Any]:
    value = raw.get(key, {})
    if not isinstance(value, Mapping):
        prefix = f"{where}." if where else ""
        raise PolicyError(f"{prefix}{key}: expected a table")
    return value


def _list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise PolicyError(f"{where}: expected a list")
    return value


def _str(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise PolicyError(f"{where}: expected a string")
    return value


def _bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise PolicyError(f"{where}: expected true or false")
    return value


def _int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PolicyError(f"{where}: expected a non-negative integer")
    return value


def _opt_int(value: Any, where: str) -> int | None:
    return None if value is None else _int(value, where)


def _verdict(value: Any, where: str) -> Verdict:
    try:
        return Verdict.parse(_str(value, where))
    except ValueError as exc:
        raise PolicyError(f"{where}: {exc}") from None


def _enum(cls: type[_E], value: Any, where: str) -> _E:
    try:
        return cls(_str(value, where))
    except ValueError:
        allowed = ", ".join(m.value for m in cls)
        raise PolicyError(f"{where}: unknown value {value!r} (expected one of: {allowed})") from None
