import re
from pathlib import Path
from typing import Any

import pytest

from airlock import ArgRole, Effect, PolicyError, Verdict, default_policy, load_policy, policy_from_dict


def minimal(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "scope": {"protected_paths": ["/p"]},
        "tools": {"read_file": {"effects": ["read"], "args": {"path": "path"}}},
    }
    data.update(overrides)
    return data


def test_bundled_policy_loads_and_lints_clean() -> None:
    policy = default_policy()
    assert policy.lint() == []
    send = policy.tools["send_email"]
    assert send.effects == {Effect.EGRESS}
    assert send.irreversible
    assert send.args["to"] is ArgRole.RECIPIENT


def test_defaults_are_conservative() -> None:
    policy = policy_from_dict(minimal())
    assert policy.unknown_tool is Verdict.DENY
    assert policy.irreversible is Verdict.ESCALATE
    assert policy.provenance is Verdict.ESCALATE
    assert policy.max_denials == 3
    assert policy.budget.max_spend == 0.0


@pytest.mark.parametrize(
    ("data", "where"),
    [
        (minimal(polcy={}), "polcy"),
        (minimal(scope={"read_path": []}), "scope.read_path"),
        (minimal(tools={"t": {"effects": ["teleport"]}}), "tools.t.effects[0]"),
        (minimal(tools={"t": {"effects": ["read"], "args": {"x": "colour"}}}), "tools.t.args.x"),
        (minimal(tools={"t": {"effects": []}}), "tools.t.effects"),
        (minimal(tools={"t": {"effects": ["read"], "irreversible": "yes"}}), "tools.t.irreversible"),
        (minimal(tools={}), "tools"),
        (minimal(policy={"unknown_tool": "maybe"}), "policy.unknown_tool"),
        (minimal(budget={"max_spend": -5}), "budget.max_spend"),
        (minimal(budget={"max_actions": 1.5}), "budget.max_actions"),
        (minimal(checks={"provenance": {"roles": ["nonsense"]}}), "checks.provenance.roles[0]"),
        (minimal(scope={"domains": "example.org"}), "scope.domains"),
    ],
)
def test_errors_name_the_offending_key(data: dict[str, Any], where: str) -> None:
    with pytest.raises(PolicyError, match="^" + re.escape(where)):
        policy_from_dict(data)


def test_lint_flags_risky_settings() -> None:
    policy = policy_from_dict(
        {
            "policy": {"unknown_tool": "allow"},
            "checks": {"irreversible": "allow"},
            "tools": {
                "pay": {"effects": ["spend"], "args": {"to": "recipient"}},
                "post": {"effects": ["egress"], "args": {"body": "content"}},
            },
        }
    )
    text = "\n".join(policy.lint())
    for expected in [
        "unknown_tool = allow",
        "irreversible = allow",
        "protected_paths is empty",
        "no 'amount'",
        "no 'payee'",
        "deletes or spends but is not irreversible",
        "egress with no url/recipient",
    ]:
        assert expected in text


def test_load_policy_reports_toml_errors(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("[policy\nname = 1\n")
    with pytest.raises(PolicyError, match=r"bad\.toml"):
        load_policy(bad)
