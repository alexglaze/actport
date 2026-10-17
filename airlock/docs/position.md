# What guardrails tool-using agents need

Most of what gets called "guardrails" for language models is filtering text:
classify the prompt, classify the response, block what matches. That made
sense when a model's worst output was a bad paragraph. Once a model can call
tools, its worst output is an email that went to the wrong person, a
directory that no longer exists, or a payment that cleared. Text filters
still matter, but they look in the wrong place. The failure happens at the
action, so that is where a control has to sit.

This note is my view of what that action layer needs. airlock implements
the parts that fit in a library. The last sections cover the parts that
don't.

## Three assumptions

**1. Treat the model as untrusted at the action boundary.** This is not a
claim that models are malicious. It follows from three things that are true
today:

- Agents read text they did not choose: web pages, inboxes, files, other
  agents' output. That text can steer them, and today's models cannot be
  relied on to tell instructions from data.
- Agents make ordinary mistakes: they misread the task, over-generalise, or
  "helpfully" do more than asked.
- We cannot yet verify from the outside that a model's goals match its
  principal's. Until we can, an action control that only works when the
  model behaves is not really a control.

The useful consequence: you don't need to know *why* an agent proposed a bad
action to stop it. The gateway judges actions, not intentions.

**2. The gateway has to be the only path to effects.** If an agent has a
guarded `send_email` tool and also an unguarded shell with network access,
the gateway is advisory. Making it the only path is a deployment property
(sandboxing, network policy, credentials held by the gateway rather than the
agent), not something a library can promise. It is still the assumption
everything else rests on.

**3. People review a few things well and many things badly.** Human approval
is the strongest control available and the easiest to wear out. A design
that asks for approval on every step will get rubber-stamped. Review load is
a cost to measure and minimise, not a free safety knob.

## The guardrails

### 1. Authority comes from the principal, not from data

The person who gave the task decides who receives the report, how much gets
paid, and which files change. A document the agent read does not get a vote,
however it is phrased. In practice: track where each argument value came
from, and when a value that controls an action (a recipient, a payee, an
amount, a path, a command) was copied from tool output rather than from the
principal, a person confirms it before it runs.

*In airlock:* the provenance check ([design](design.md#provenance)). It is
coarse, because it only sees verbatim copies, so it is one layer among
several, never the only one.

### 2. Least privilege per task, not per agent

An agent's credentials usually cover everything it might ever do. A task
needs a sliver of that. Scope should be granted per task (these paths, these
domains, these recipients) and bounded by a ceiling the task cannot exceed.
The evaluation shows why this matters: the same out-of-policy email is
caught only by review under a domain-wide scope, and deterministically under
a scope listing the one recipient the task named.

*In airlock:* the policy scope is a ceiling. Each session may narrow it, and
a session that asks for more is refused when it starts.

### 3. Classify actions by effect and reversibility, and scale oversight to stakes

"Can this be undone?" is the most useful single question about an action.
Reads are cheap to allow. Writes inside a scratch directory are cheap to
allow. Deleting, sending, and paying cannot be taken back, so they deserve a
second look. Tools should declare what they do, and policy should be written
against those declarations, not against tool names. Then a new tool gets the
right treatment the moment it is described.

*In airlock:* every tool declares effects and argument roles. Irreversible
tools escalate by default.

### 4. Oversight must be out of the agent's reach

The policy, the audit log, and the approval channel are part of the
oversight mechanism. An agent that can edit them can switch its own
oversight off, by accident or otherwise. Attempts to modify oversight
deserve more than a denial. They are a strong signal that something has gone
wrong, so the session should stop.

*In airlock:* protected paths. A write or delete aimed at one, or at a
directory above one, halts the session, and so does a command that names one
in any argument. A program that changes a protected file without naming it
is beyond what argument inspection can see. That's one reason oversight
should also live outside the agent's reach entirely.

### 5. Fail closed. Deterministic layers first, model judgment second.

Every error path should end in "no", or at worst in front of a person: an
unknown tool, an argument that won't parse, a check that crashes, a reviewer
that errors or gives anything but an explicit yes, an action that can't be
recorded. Model-based monitors
are useful because they catch what rules don't anticipate. But they read the
same untrusted content the agent reads, so they can be misled by it. They
should only ever *add* caution, never overrule a deterministic denial.

*In airlock:* an exception in a check, a monitor, or a reviewer is a
denial, and a failed audit write halts the session. A monitor whose model
can't be reached escalates to a person by default (`on_error`, which can be
set to deny). Monitors run only when no deterministic check has already
denied, and a monitor's verdict can only raise the result, never lower it.

### 6. Bound the damage in volume, not just in kind

Some failures are a single bad action. Others are a thousand fine ones: a
loop, a retry storm, spending that adds up. Budgets on actions, calls per
tool, and money bound the worst case regardless of cause. Repeated denials
in a session are also a signal. An agent that keeps proposing out-of-policy
actions is either stuck or not pursuing the task. Either way, stop and hand
the session back to a person rather than letting it keep trying.

*In airlock:* per-session budgets, and a circuit breaker that halts after N
denials (including rejected reviews).

### 7. Make every action attributable

After something goes wrong, the first questions are what was proposed, what
was decided, by which rule, and who approved it. That record should exist
for every action, and it should be hard to rewrite quietly.

*In airlock:* an append-only, hash-chained audit log, optionally keyed
(HMAC). Each decision records its arguments, findings, and any review. Tool
outputs are logged as digests by default, so the log doesn't also become a
copy of everything the agent read. The arguments are the decision being
audited, so they're logged in full, and the log is sensitive accordingly.

### 8. Measure the guardrails, including what they cost

A guardrail without numbers is a belief. The useful numbers come in a set:

- how many out-of-policy actions get through,
- how much legitimate work still gets done,
- how many reviews it takes to get there,
- and how much of the safety depends on the reviewer being good.

Reporting only the first number hides the trade-offs that decide whether
anyone will actually run the thing.

*In airlock:* the evaluation suite runs every scenario unguarded, with a
perfect reviewer, with a reviewer who approves everything, and with no
reviewer at all, and reports all four numbers for each
([evaluation](evaluation.md)).

### 9. Design the review for the reviewer

A review request should say what the action is, what it affects, whether it
can be undone, and exactly why it was flagged. A reviewer who sees "send
email?" learns nothing. A reviewer who sees "the recipient was copied from
the document you asked me to send, not from your instructions" can decide.

*In airlock:* `ReviewRequest.render()` puts the task, the action, its
effects, and every finding in front of the reviewer.

## What a library can't do

These matter at least as much, and none of them live in this repository:

- **Model-level alignment.** Training models that want what their principals
  want and that resist manipulation. Action controls exist because this is
  unfinished, not as a substitute for it.
- **Capability evaluation before deployment.** Knowing what a model can do
  before giving it tools, and gating deployment on it.
- **Isolation.** OS sandboxes, network egress policy, and credentials scoped
  to the task and held outside the agent. This is what makes assumption 2
  true.
- **Accurate tool declarations.** airlock trusts each tool's declared
  effects. A tool described as read-only that actually writes defeats every
  check here. Declarations need review like any other security-relevant
  config.
- **Organisation.** Who reviews, how fast, with what context. What happens
  after a halt. How incidents are written up and fed back into policy.
  Staged rollout of agent permissions.

## Open problems

- **Provenance beyond copying.** Whole-token matching misses values the
  agent derived from untrusted text. Doing this properly means separating
  the component that plans from the component that touches untrusted data,
  so untrusted data can't reach control decisions at all. That is an
  architecture change, not a filter.
- **Monitors that can be talked to.** Anything that reads the trajectory can
  be addressed by the trajectory. Fencing and instructions help. They don't
  solve it.
- **Reviewer quality.** The evaluation's two reviewer models (perfect and
  rubber-stamp) bracket reality, but where real reviewers fall, and how that
  drifts with fatigue, is an empirical question this repository can't
  answer.
- **Setting scope automatically.** Per-task scope is only as good as
  whatever derives it. If the agent proposes its own scope, it has to be
  checked against something the agent doesn't control.
- **Harm from sequences.** Some bad outcomes are made of steps that are each
  individually fine. Budgets bound the volume. They don't recognise the
  pattern.

## Related ideas

- J. P. Anderson, *Computer Security Technology Planning Study* (1972): the
  reference monitor, meaning a mediator that is always invoked,
  tamper-proof, and small enough to verify. airlock aims at the first two
  and tries to stay small.
- Capability-based security: authority as an explicit, narrow grant, not
  ambient permission.
- S. Willison's "dual LLM" pattern (2023) and Debenedetti et al.,
  *Defeating Prompt Injections by Design* (CaMeL, 2025): separating
  privileged planning from untrusted data processing, the principled version
  of what the provenance check approximates.
- Greenblatt et al., *AI Control: Improving Safety Despite Intentional
  Subversion* (2023): measuring safety protocols, including trusted
  monitoring, under the assumption that the model may be working against
  them.
- Debenedetti et al., *AgentDojo* (2024): measuring agent utility and
  security together rather than security alone.
