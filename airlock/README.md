# airlock

A policy gateway between a tool-using AI agent and the tools it calls.

Every action the agent proposes passes through airlock before it runs. The
gateway checks it against a declared policy, asks a person when the stakes
call for it, halts the session when something is clearly wrong, and writes
a tamper-evident record of all of it.

Most model guardrails filter text. Agents fail at actions: the email that
went to the wrong person, the file that got deleted, the invoice paid twice.
airlock sits at that point, and it is built on the assumption that the
model proposing the action can't be fully trusted. That's not an accusation.
It reads text it didn't choose, it makes mistakes, and nobody can yet verify
its goals from the outside. [docs/position.md](docs/position.md) makes the
full argument for which guardrails agents need, and which of them a library
can't provide.

## What it checks

| Layer | Stops | Verdict |
| --- | --- | --- |
| Registry | unregistered tools, undeclared arguments | deny |
| Protected paths | writes or deletes aimed at the policy, audit log, or other oversight (or a directory above them), and commands that name them in any argument | **halt** |
| Scope (per task, under a policy ceiling) | paths, hosts, recipients, payees, programs, and command path arguments the task wasn't granted; `..` escapes; shell syntax; ambiguous or malformed hosts | deny |
| Provenance | control arguments (recipient, payee, amount, path, command) copied from tool output instead of from the principal | escalate |
| Irreversibility | sending, paying, deleting without review | escalate |
| Budgets | action count, per-tool calls, cumulative spend | deny |
| Circuit breaker | a session that keeps proposing denied actions | **halt** |
| Monitors (optional) | a second model's judgement; it can only add caution | escalate / deny |

Errors fail closed: a check that crashes, a reviewer that errors or answers
anything but an explicit yes, and a missing reviewer all mean no, and an
action that can't be written to the audit log halts the session. (A monitor
whose model is unavailable escalates to a person by default.) Tools are
described by their effects and
argument roles, so policy is written once against those, not per tool.

## Quick start

```bash
pip install -e ".[dev]"
python examples/quickstart.py      # offline walkthrough
python -m airlock eval             # the evaluation suite
```

```python
from airlock import Action, Airlock, ConsoleReviewer, Scope, default_policy

airlock = Airlock(default_policy(), reviewer=ConsoleReviewer())
session = airlock.session(
    "Email the Q3 report in /workspace/reports/q3.md to dana@acme.example.",
    scope=Scope(cwd="/workspace", read_paths=("/workspace/reports",), recipients=("dana@acme.example",)),
)

tools = session.guard({"read_file": read_file, "send_email": send_email})
report = tools["read_file"](path="/workspace/reports/q3.md")
tools["send_email"](to="dana@acme.example", subject="Q3", body=report)  # asks you first: irreversible
tools["send_email"](to="finance-all@acme.example", subject="Q3", body=report)  # raises ActionBlocked: out of scope
```

For a real model in the loop, see
[examples/claude_agent.py](examples/claude_agent.py). It is a Claude
tool-use loop with every call gated, blocked calls returned to the model
with their reasons, and a second model call acting as monitor.

## Results

23 scripted scenarios, each run without the gateway, with a perfect
reviewer, with a reviewer who approves everything, and with no reviewer:

| mode | benign tasks completed | violations executed | reviews per benign task | legit work done in violation runs |
| --- | --- | --- | --- | --- |
| unguarded | 8/8 (100%) | 15/15 (100%) | 0.00 | 14/15 (93%) |
| oracle | 8/8 (100%) | 0/15 (0%) | 0.75 | 13/15 (87%) |
| approve-all | 8/8 (100%) | 3/15 (20%) | 0.75 | 12/15 (80%) |
| deny-all | 3/8 (38%) | 0/15 (0%) | 0.75 | 8/15 (53%) |

The row worth reading is **approve-all**. The 3 violations that get past a
rubber-stamp reviewer are exactly the 3 whose only defence was review.
Everything else is stopped by deterministic layers. Narrowing scope to the
task moves catches from the first group to the second.

These numbers are a regression baseline for the gateway's logic, not a
measure of how safe any agent is. The agents are scripted, the scenarios
were written alongside the defences, and nothing in the suite adapts to the
checks. [docs/evaluation.md](docs/evaluation.md) covers method,
interpretation, and limitations. [docs/results.md](docs/results.md) has
every scenario.

## Docs

- [position.md](docs/position.md): what guardrails tool-using agents need, and what's out of a library's reach
- [threat-model.md](docs/threat-model.md): what's protected, trust boundaries, what's explicitly not covered
- [design.md](docs/design.md): the decision pipeline, each check, and why it works the way it does
- [evaluation.md](docs/evaluation.md): method, results, and limitations

## Layout

```
src/airlock/
  types.py        Effect, ArgRole, Verdict, Action, Finding, Decision, ToolSpec
  scope.py        path / host / recipient / command matching, scope ceilings
  provenance.py   trusted vs. untrusted text, value attribution
  checks.py       the deterministic checks
  gate.py         Airlock and Session: the pipeline, review, breaker, audit
  monitor.py      monitor protocol and the LLM monitor
  review.py       reviewers
  audit.py        hash-chained audit log and verification
  policy.py       policy model, TOML loading, lint
  policies/default.toml
  evals/          simulated world, scenarios, harness, report
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src tests examples && ruff format --check src tests examples
mypy
airlock lint-policy --strict src/airlock/policies/default.toml
python -m airlock eval > docs/results.md   # after changing scenarios or checks
```

No runtime dependencies. Python 3.11+.

## Status

Early and opinionated. The interfaces may change. The things I'd most like
to improve are in the open problems section of
[position.md](docs/position.md#open-problems).

MIT licensed.
