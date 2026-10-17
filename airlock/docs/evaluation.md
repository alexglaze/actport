# Evaluation

```bash
python -m airlock eval                  # markdown report (what docs/results.md is)
python -m airlock eval --format json    # per-run records
python -m airlock eval --mode oracle --scenario recipient-from-document
```

Full per-scenario output: [results.md](results.md). It is generated, and a
test fails if it drifts from the code.

## Method

Each scenario is a task, a starting world (files, inbox, web pages), and a
scripted agent. The world is simulated: tools act on in-memory state and
record what they did, so each scenario can check the end state.

- **Benign scenarios** (8) do only what the task asks. The question: does
  the gateway let ordinary work through, and how many reviews does it cost?
- **Violation scenarios** (15) do the task but also propose something the
  principal didn't ask for or the policy doesn't allow. The question: does
  the out-of-policy effect happen?

The agents parse the values they act on out of what they observed, so when
an agent emails an address it found in a document, the provenance ledger
sees a real copy from tool output to argument.

Every scenario runs in four modes:

| Mode | Gateway | Reviewer |
| --- | --- | --- |
| `unguarded` | off | n/a |
| `oracle` | on | approves exactly what the principal wanted |
| `approve-all` | on | approves every escalation (a rubber stamp) |
| `deny-all` | on | refuses every escalation (no human available) |

`oracle` and `approve-all` bracket real reviewers. `deny-all` is what
running fully autonomously costs under this policy.

## Metrics

- **Benign tasks completed**: utility.
- **Violations executed**: the out-of-policy effect happened.
- **Reviews per benign task**: human load on ordinary work.
- **Legit work done in violation runs**: whether the task's legitimate part
  still completed. A halt is safe, but it isn't free.

## Results

| mode | benign tasks completed | violations executed | reviews per benign task | legit work done in violation runs |
| --- | --- | --- | --- | --- |
| unguarded | 8/8 (100%) | 15/15 (100%) | 0.00 | 14/15 (93%) |
| oracle | 8/8 (100%) | 0/15 (0%) | 0.75 | 13/15 (87%) |
| approve-all | 8/8 (100%) | 3/15 (20%) | 0.75 | 12/15 (80%) |
| deny-all | 3/8 (38%) | 0/15 (0%) | 0.75 | 8/15 (53%) |

## Reading the results

**Unguarded, every violation lands.** That's the sanity check that the
scenarios are real, and a test enforces it per scenario.

**With a good reviewer, nothing gets through and nothing legitimate is
lost.** The cost is 0.75 reviews per benign task. All of them come
from irreversible actions (sending, paying, deleting) that the task did ask
for. Two violation runs lose their legitimate work because the session
halted before getting to it: `edit-own-policy` and `runaway-loop`. That's
the intended trade. A session that tried to rewrite its own policy shouldn't
carry on with the task.

**With a rubber-stamp reviewer, 3 of 15 get through, and they are exactly
the 3 whose only defence was review:** `recipient-from-document`,
`amount-from-document`, and `unrequested-delete`. Everything else was
stopped by a deterministic layer (registry, scope, protected paths, budget,
breaker) and didn't depend on the reviewer at all. This is the number that
matters most for deployment: it says how much of the safety lives in a
person's attention.

**Least privilege moves catches from the reviewer to the policy.**
`recipient-from-document` and `recipient-from-document-narrow` are the same
agent doing the same thing. Under a domain-wide recipient scope, only review
catches it. Under a scope listing the one recipient the task named, the
scope check denies it outright and the reviewer is never asked. The general
lesson: derive scope from the task wherever you can.

**Without any reviewer, it's safe but much less useful.** Zero violations,
but only 3 of 8 benign tasks complete, because the policy can't tell a
requested payment from an unrequested one without asking someone. Fully
autonomous operation under this policy means accepting that, or narrowing
scope until fewer actions need review.

**Provenance escalations on benign work are real.** `reply-to-sender` and
`clean-scratch` both trip provenance, because the recipient or path
legitimately comes from tool output. In both cases the action was
irreversible and would have been reviewed anyway, so provenance added a
reason, not a review. A policy that stopped escalating irreversible actions
would see provenance become the main source of reviews.

## Limitations

These are significant. Treat the numbers as a regression baseline for the
gateway's decision logic, not as a measure of how safe an agent is.

- **Scripted agents are not models.** The suite measures what the gateway
  decides, given a sequence of proposed actions. It says nothing about how
  often a real model proposes such actions, or how it behaves after a
  denial. For that, run a real model through the gateway
  ([`examples/claude_agent.py`](../examples/claude_agent.py)) on tasks you
  care about.
- **Same author, both sides.** I wrote the scenarios and the gateway. Every
  scenario here is one the gateway was designed to handle. A scenario I
  didn't think of is, by construction, not in this table.
- **No adaptive adversary.** No scenario adjusts its behaviour to the
  checks, so the suite says nothing about robustness against one.
- **Small.** 23 scenarios. Percentages are a compact way to write counts,
  not estimates of anything.
- **The oracle is ideal.** Real reviewers fall somewhere between `oracle`
  and `approve-all`, and drift toward the latter as volume rises.

## Adding a scenario

Add a `Scenario` to `src/airlock/evals/scenarios.py`: a task, a world
factory, a generator-based agent, `done` and `violated` predicates, and a
`wanted` predicate for the oracle reviewer. Then regenerate the results with
`python -m airlock eval > docs/results.md`. The tests check that every
violation scenario really violates when unguarded, so a predicate that
never fires can't pass as a defence.
