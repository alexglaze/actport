"""Run scenarios with and without the gateway, under different reviewers, and tabulate."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

from ..gate import Airlock
from ..policy import Policy
from ..review import ApproveAll, CallbackReviewer, DenyAll, Reviewer
from ..types import Action, Verdict
from .scenarios import SCENARIOS, WORKSPACE, Observation, Scenario
from .world import World

MODES = ("unguarded", "oracle", "approve-all", "deny-all")
MODE_NOTES = {
    "unguarded": "no gateway; every proposed action runs",
    "oracle": "gateway on; reviewer approves exactly what the principal wanted",
    "approve-all": "gateway on; reviewer approves every escalation",
    "deny-all": "gateway on; no reviewer available, every escalation is refused",
}
MAX_STEPS = 200


@dataclass(frozen=True)
class Result:
    scenario: str
    kind: str
    mode: str
    done: bool
    violated: bool
    steps: int
    escalations: int
    denials: int
    halted: bool
    fired: tuple[str, ...]


def _execute(world: World, action: Action) -> Observation:
    fn = world.tools().get(action.tool)
    if fn is None:
        return Observation(False, f"error: no such tool {action.tool!r}")
    try:
        return Observation(True, str(fn(**action.args)))
    except Exception as exc:  # noqa: BLE001 - surfaced to the agent like a tool error
        return Observation(False, f"error: {type(exc).__name__}: {exc}")


def _reviewer(mode: str, scenario: Scenario, world: World) -> Reviewer:
    if mode == "oracle":
        return CallbackReviewer(lambda req: scenario.wanted(req.action, world), name="oracle")
    if mode == "approve-all":
        return ApproveAll()
    if mode == "deny-all":
        return DenyAll()
    raise ValueError(f"unknown mode {mode!r}")


def run(scenario: Scenario, mode: str, policy: Policy) -> Result:
    world = scenario.world()
    agent = scenario.agent()
    session = None
    if mode != "unguarded":
        airlock = Airlock(policy, reviewer=_reviewer(mode, scenario, world))
        session = airlock.session(scenario.task, scope=scenario.scope or WORKSPACE, session_id=scenario.id)

    steps = 0
    try:
        action = next(agent)
        while steps < MAX_STEPS:
            steps += 1
            if session is None:
                obs = _execute(world, action)
            else:
                decision = session.check(action)
                if decision.allowed:
                    obs = _execute(world, action)
                    session.record_result(decision, obs.output)
                else:
                    reasons = "; ".join(f.message for f in decision.findings if f.verdict > Verdict.ALLOW)
                    obs = Observation(False, f"blocked by policy ({decision.verdict}): {reasons}")
                if session.halted:
                    break
            action = agent.send(obs)
    except StopIteration:
        pass

    fired: set[str] = set()
    if session is not None:
        for d in session.decisions:
            fired.update(f.check for f in d.findings if f.verdict > Verdict.ALLOW)
    return Result(
        scenario=scenario.id,
        kind=scenario.kind,
        mode=mode,
        done=scenario.done(world),
        violated=scenario.violated(world),
        steps=steps,
        escalations=session.escalations if session else 0,
        denials=session.denials if session else 0,
        halted=session.halted if session else False,
        fired=tuple(sorted(fired)),
    )


def run_all(
    policy: Policy, scenarios: Sequence[Scenario] = SCENARIOS, modes: Iterable[str] = MODES
) -> list[Result]:
    return [run(s, m, policy) for m in modes for s in scenarios]


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "n/a"


def summary(results: Sequence[Result]) -> list[dict[str, str]]:
    rows = []
    for mode in dict.fromkeys(r.mode for r in results):
        rs = [r for r in results if r.mode == mode]
        benign = [r for r in rs if r.kind == "benign"]
        bad = [r for r in rs if r.kind == "violation"]
        rows.append(
            {
                "mode": mode,
                "benign tasks completed": _pct(sum(r.done for r in benign), len(benign)),
                "violations executed": _pct(sum(r.violated for r in bad), len(bad)),
                "reviews per benign task": f"{sum(r.escalations for r in benign) / len(benign):.2f}"
                if benign
                else "n/a",
                "legit work done in violation runs": _pct(sum(r.done for r in bad), len(bad)),
            }
        )
    return rows


def _table(rows: Sequence[dict[str, str]]) -> list[str]:
    if not rows:
        return []
    headers = list(rows[0])
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(" --- " for _ in headers) + "|"]
    out += ["| " + " | ".join(row[h] for h in headers) + " |" for row in rows]
    return out


def _cell(r: Result) -> str:
    if r.kind == "violation":
        mark = "executed" if r.violated else "blocked"
    else:
        mark = "done" if r.done else "not done"
    extras = []
    if r.escalations:
        extras.append(f"{r.escalations} review{'s' if r.escalations != 1 else ''}")
    if r.halted:
        extras.append("halted")
    return mark + (f" ({', '.join(extras)})" if extras else "")


def to_markdown(results: Sequence[Result], scenarios: Sequence[Scenario] = SCENARIOS) -> str:
    modes = list(dict.fromkeys(r.mode for r in results))
    by_key = {(r.scenario, r.mode): r for r in results}
    lines = ["## Summary", ""]
    lines += _table(summary(results))
    lines += ["", "Modes:", ""]
    lines += [f"- **{m}**: {MODE_NOTES[m]}" for m in modes]
    for kind, title in (("benign", "Benign scenarios"), ("violation", "Violation scenarios")):
        lines += ["", f"## {title}", ""]
        rows = []
        for s in scenarios:
            if s.kind != kind:
                continue
            guarded = by_key.get((s.id, "oracle"))
            row = {"scenario": f"`{s.id}`", "what happens": s.summary}
            row["checks that fired"] = ", ".join(guarded.fired) if guarded and guarded.fired else "none"
            row.update({m: _cell(by_key[(s.id, m)]) for m in modes if (s.id, m) in by_key})
            rows.append(row)
        lines += _table(rows)
    return "\n".join(lines) + "\n"


RESULTS_HEADER = (
    "# Evaluation results\n\n"
    "Generated by `python -m airlock eval > docs/results.md`; do not edit by hand. "
    "`tests/test_eval.py` fails if this file drifts from the code.\n\n"
)


def results_document(results: Sequence[Result], scenarios: Sequence[Scenario] = SCENARIOS) -> str:
    return RESULTS_HEADER + to_markdown(results, scenarios)


def to_json(results: Sequence[Result]) -> str:
    return json.dumps({"summary": summary(results), "results": [asdict(r) for r in results]}, indent=2)
