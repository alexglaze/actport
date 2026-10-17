"""airlock: a policy gateway between a tool-using AI agent and the tools it calls."""

from .audit import AuditLog, verify
from .gate import ActionBlocked, Airlock, ScopeError, Session
from .monitor import LLMMonitor, Monitor, MonitorContext
from .policy import Budget, Policy, PolicyError, load_policy, policy_from_dict
from .review import ApproveAll, CallbackReviewer, ConsoleReviewer, DenyAll, Reviewer, ReviewRequest
from .scope import Scope
from .types import Action, ArgRole, Decision, Effect, Finding, Review, ToolSpec, Verdict

__version__ = "0.1.0"


def default_policy() -> Policy:
    """The bundled policy used by the examples and the evaluation suite."""
    from importlib.resources import files

    with (files(__package__) / "policies" / "default.toml").open("rb") as fh:
        import tomllib

        return policy_from_dict(tomllib.load(fh))


__all__ = [
    "Action",
    "ActionBlocked",
    "Airlock",
    "ApproveAll",
    "ArgRole",
    "AuditLog",
    "Budget",
    "CallbackReviewer",
    "ConsoleReviewer",
    "Decision",
    "DenyAll",
    "Effect",
    "Finding",
    "LLMMonitor",
    "Monitor",
    "MonitorContext",
    "Policy",
    "PolicyError",
    "Review",
    "ReviewRequest",
    "Reviewer",
    "Scope",
    "ScopeError",
    "Session",
    "ToolSpec",
    "Verdict",
    "default_policy",
    "load_policy",
    "policy_from_dict",
    "verify",
]
