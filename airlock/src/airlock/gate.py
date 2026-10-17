"""The gateway: every proposed action goes through ``Session.check`` before it runs."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from typing import Any

from .audit import AuditLog
from .checks import DEFAULT_CHECKS, Check, Context, Usage, spend_of
from .monitor import Monitor, MonitorContext, Step
from .policy import Policy
from .provenance import Provenance
from .review import Reviewer, ReviewRequest
from .scope import Scope
from .types import Action, Decision, Finding, Review, Verdict


class ScopeError(ValueError):
    """A session asked for more than the policy's scope ceiling allows."""


class ActionBlocked(RuntimeError):
    """Raised by guarded tools when the gateway does not allow a call."""

    def __init__(self, decision: Decision) -> None:
        super().__init__(decision.explain())
        self.decision = decision


def _text(output: Any) -> str:
    if isinstance(output, str):
        return output
    try:
        return json.dumps(output, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(output)


class Airlock:
    """Holds the policy and shared machinery; hands out one ``Session`` per task."""

    def __init__(
        self,
        policy: Policy,
        *,
        reviewer: Reviewer | None = None,
        audit: AuditLog | None = None,
        monitors: Sequence[Monitor] = (),
        checks: Sequence[Check] = DEFAULT_CHECKS,
        log_outputs: bool = False,
    ) -> None:
        self.policy = policy
        self.reviewer = reviewer
        self.audit = audit if audit is not None else AuditLog()
        self.monitors = tuple(monitors)
        self.checks = tuple(checks)
        self.log_outputs = log_outputs

    def session(self, task: str, *, scope: Scope | None = None, session_id: str | None = None) -> Session:
        """Start a session. A per-task ``scope`` may only narrow the policy's scope."""
        if scope is None:
            scope = self.policy.scope
        else:
            problems = scope.exceeds(self.policy.scope)
            if problems:
                raise ScopeError("session scope exceeds the policy ceiling: " + "; ".join(problems))
        scope = scope.with_protected(self.policy.scope.protected_paths)
        return Session(self, task, scope, session_id or uuid.uuid4().hex[:12])


class Session:
    def __init__(self, airlock: Airlock, task: str, scope: Scope, session_id: str) -> None:
        self.airlock = airlock
        self.policy = airlock.policy
        self.id = session_id
        self.task = task
        self.scope = scope
        self.provenance = Provenance()
        self.provenance.add_trusted(task, "task")
        self.usage = Usage()
        self.decisions: list[Decision] = []
        self.history: list[Step] = []
        self.denials = 0
        self.halted = False
        self._log(
            "session_start",
            {"task": task, "policy": self.policy.name, "scope": _scope_summary(scope)},
        )

    # -- principal input ---------------------------------------------------

    def tell(self, text: str) -> None:
        """Add a later message from the principal. It carries the same authority as the task."""
        self.provenance.add_trusted(text, f"principal#{len(self.history)}")
        self._log("principal_message", {"text": text})

    # -- the decision pipeline ---------------------------------------------

    def check(self, action: Action) -> Decision:
        step = len(self.decisions) + 1
        if self.halted:
            finding = Finding("session", Verdict.DENY, "session is halted")
            return self._finish(Decision(step, action, Verdict.DENY, (finding,)))

        spec = self.policy.tools.get(action.tool)
        ctx = Context(self.policy, self.scope, spec, self.provenance, self.usage)
        findings: list[Finding] = []
        for check in self.airlock.checks:
            findings += self._run(getattr(check, "__name__", "check"), partial(check, ctx, action))

        if _worst(findings) < Verdict.DENY:
            mctx = MonitorContext(self.task, action, spec, tuple(findings), tuple(self.history))
            for monitor in self.airlock.monitors:
                findings += self._run(monitor.name, partial(monitor.assess, mctx))

        verdict = _worst(findings)
        review: Review | None = None
        if verdict is Verdict.ESCALATE:
            review = self._review(step, action, tuple(findings))
            verdict = Verdict.ALLOW if review.approved else Verdict.DENY

        if verdict is Verdict.DENY:
            self.denials += 1
            limit = self.policy.max_denials
            if limit is not None and self.denials >= limit:
                findings.append(
                    Finding("circuit_breaker", Verdict.HALT, f"{self.denials} denied actions in this session")
                )
                verdict = Verdict.HALT

        if verdict is Verdict.ALLOW and spec is not None:
            self.usage.actions += 1
            self.usage.per_tool[action.tool] += 1
            self.usage.spend += spend_of(spec, action)

        return self._finish(Decision(step, action, verdict, tuple(findings), review))

    def _run(self, name: str, fn: Callable[[], list[Finding]]) -> list[Finding]:
        try:
            return list(fn())
        except Exception as exc:  # noqa: BLE001 - fail closed on any checker bug
            return [Finding(name, Verdict.DENY, f"check failed, denying: {type(exc).__name__}: {exc}")]

    def _review(self, step: int, action: Action, findings: tuple[Finding, ...]) -> Review:
        reviewer = self.airlock.reviewer
        if reviewer is None:
            return Review(
                approved=False, reviewer="none", note="escalation needed but no reviewer configured"
            )
        request = ReviewRequest(
            self.id, self.task, step, action, self.policy.tools.get(action.tool), findings
        )
        try:
            return reviewer.review(request)
        except Exception as exc:  # noqa: BLE001 - a broken reviewer is a rejection
            return Review(approved=False, reviewer="error", note=f"{type(exc).__name__}: {exc}")

    def _finish(self, decision: Decision) -> Decision:
        if decision.verdict is Verdict.HALT:
            self.halted = True
        self.decisions.append(decision)
        self.history.append(Step(decision.action, decision.verdict))
        self._log("decision", _decision_record(decision))
        if decision.verdict is Verdict.HALT:
            self._log("halt", {"step": decision.step})
        return decision

    # -- results -----------------------------------------------------------

    def record_result(self, decision: Decision, output: Any) -> None:
        """Record what an allowed action returned, so later checks know where values came from."""
        if not decision.allowed:
            raise ValueError("only allowed actions produce results")
        text = _text(output)
        spec = self.policy.tools.get(decision.action.tool)
        source = f"{decision.action.tool}#{decision.step}"
        if spec is not None and spec.trusted_output:
            self.provenance.add_trusted(text, source)
        else:
            self.provenance.add_untrusted(text, source)
        index = decision.step - 1
        if 0 <= index < len(self.history):
            self.history[index] = Step(decision.action, decision.verdict, text)
        record: dict[str, Any] = {
            "step": decision.step,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "chars": len(text),
        }
        if self.airlock.log_outputs:
            record["output"] = text
        self._log("result", record)

    def call(self, tools: Mapping[str, Callable[..., Any]], tool: str, **args: Any) -> Any:
        """Check, run, and record one call. Raises ``ActionBlocked`` if not allowed."""
        decision = self.check(Action(tool, args))
        if not decision.allowed:
            raise ActionBlocked(decision)
        output = tools[tool](**args)
        self.record_result(decision, output)
        return output

    def guard(self, tools: Mapping[str, Callable[..., Any]]) -> dict[str, Callable[..., Any]]:
        """Wrap a dict of tool functions so every call goes through this session."""

        def wrap(name: str) -> Callable[..., Any]:
            def guarded(**args: Any) -> Any:
                return self.call(tools, name, **args)

            guarded.__name__ = name
            guarded.__doc__ = tools[name].__doc__
            return guarded

        return {name: wrap(name) for name in tools}

    @property
    def escalations(self) -> int:
        return sum(1 for d in self.decisions if d.escalated)

    def _log(self, event: str, data: Mapping[str, Any]) -> None:
        self.airlock.audit.append(event, {"session": self.id, **data})


def _worst(findings: Sequence[Finding]) -> Verdict:
    return max((f.verdict for f in findings), default=Verdict.ALLOW)


def _decision_record(d: Decision) -> dict[str, Any]:
    record: dict[str, Any] = {
        "step": d.step,
        "tool": d.action.tool,
        "args": dict(d.action.args),
        "verdict": str(d.verdict),
        "findings": [{"check": f.check, "verdict": str(f.verdict), "message": f.message} for f in d.findings],
    }
    if d.review is not None:
        record["review"] = {
            "approved": d.review.approved,
            "reviewer": d.review.reviewer,
            "note": d.review.note,
        }
    return record


def _scope_summary(scope: Scope) -> dict[str, Any]:
    return {k: v for k, v in vars(scope).items() if v}
