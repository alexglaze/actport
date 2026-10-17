# Design

## Shape

```
              principal (task, later messages)  ── trusted text ──┐
                              │                                   │
                              ▼                                   ▼
   agent ── proposes Action ──► Session.check ──► checks ──► monitors ──► verdict
     ▲                              │                                        │
     │                              │      ESCALATE ──► reviewer ──► allow / deny
     │                              ▼                                        │
     └──── observation ◄──── tool runs only if ALLOW ◄───────────────────────┘
                                    │
                         record_result: output → untrusted text
                                    │
                              audit log (every step)
```

An `Airlock` holds the policy, the reviewer, the monitors, and the audit
log. Each task gets a `Session`, which holds that task's scope, its
provenance ledger, its usage counters, and its history. The agent proposes
an `Action` (tool name + arguments). The session returns a `Decision`. The
tool runs only if the decision is `allow`, and its output is recorded so that
later checks know where values came from.

## Verdicts

```
allow  <  escalate  <  deny  <  halt
```

Every check returns zero or more findings, each with a verdict. The
session's verdict is the most severe finding, so adding a check can only
make the gateway stricter. Then:

- **escalate** goes to the reviewer. Approved becomes allow. Rejected, or no
  reviewer configured, becomes deny.
- **deny** increments the session's denial count. Reaching `max_denials`
  turns the decision into **halt**.
- **halt** ends the session. Every later action is denied without running
  checks.

Findings with verdict `allow` are informational. They are logged but change
nothing.

## Tools are described, not special-cased

```toml
[tools.send_email]
effects = ["egress"]
irreversible = true
args = { to = "recipient", subject = "content", body = "content" }
```

Effects: `read`, `write`, `delete`, `execute`, `egress`, `spend`.
Argument roles: `path`, `url`, `recipient`, `payee`, `amount`, `command`,
`content`.

Every check is written against effects and roles. Adding a tool means
describing it, not writing new rules, and a tool that is described wrongly
is checked wrongly. That's the main thing to review when a policy changes.
`airlock lint-policy` flags the common slips: a spending tool with no
amount, an egress tool with nothing to scope, a deleting tool not marked
irreversible.

## Checks

In order. All of them run, so a decision carries every reason, not just the
first one.

| Check | Looks at | Verdict |
| --- | --- | --- |
| `registry` | Is the tool registered? Are all arguments declared? | `unknown_tool` (default deny) / deny |
| `protected` | Does a write or delete target a protected path or a directory above one? Does a command name a protected path in any argument? | **halt** |
| `scope` | Paths (read vs. write scope, after normalising `..`), URL hosts (exact or true subdomain, strict DNS syntax, no credentials in URLs), recipients, payees, amounts, commands (allowlisted program, no shell syntax, path arguments within read scope) | deny |
| `provenance` | For consequential tools: was a control argument copied from untrusted output and not from the principal? | `checks.provenance` (default escalate) |
| `irreversible` | Is the tool declared irreversible? | `checks.irreversible` (default escalate) |
| `budget` | Session action count, per-tool call count, cumulative spend | deny |

Then, only if nothing so far is deny or worse, each **monitor** runs.

Every matcher normalises before comparing and answers "no" when it can't
parse its input. If a check raises anyway, the gateway catches the exception
and denies. The same goes for monitors and reviewers.

### Scope

The policy's `[scope]` is a ceiling. A session can be given a narrower
scope for its task:

```python
airlock.session(task, scope=Scope(cwd="/workspace", write_paths=("/workspace/out/report",),
                                  recipients=("dana@acme.example",)))
```

`Scope.exceeds(ceiling)` lists every grant the ceiling doesn't cover. A
session that would widen the ceiling raises `ScopeError` when it starts, not
halfway through. Protected paths from the policy are always merged into the
session's scope, so narrowing can never drop them.

Path entries come in two kinds. A plain entry covers that path and
everything below it. An entry containing `*`, `?` or `[` is a glob, matched
against the whole normalised path (`*` crosses `/`). Relative entries
resolve against the scope's `cwd`. Comparing a session grant to the ceiling
has to account for both kinds, so a session glob is accepted only if the
ceiling has the identical glob, or if everything it can match lies under a
plain ceiling directory. A plain session entry is accepted only under a
plain ceiling directory, because a glob ceiling can't vouch for the subtree
below a name it happens to match.

Hosts are compared in ASCII form. A non-ASCII name is accepted only if its
IDNA encoding round-trips. Names that IDNA 2003 maps onto other characters
(`ß`, fullwidth letters) are rejected, because resolvers disagree about
them, and so is anything that isn't valid DNS syntax. Rejected hosts are out
of scope, not errors.

Commands run without a shell, so shell syntax is rejected outright. The
program must be allowlisted, and every positional argument, plus any option
value that looks like a path (`--out=PATH`, `-oPATH`), must resolve inside
read scope. What an allowlisted program then does with those paths is up to
the program, so allowlist programs whose side effects you accept.

### Provenance

The session keeps two pools of text:

- **trusted**: the task, later `Session.tell()` messages from the principal,
  and output of tools declared `trusted_output = true`;
- **untrusted**: every other tool output, tagged with its source (`read_file#3`).

For each argument of a consequential tool whose role is in
`checks.provenance.roles`, the value is attributed:

| Origin | Meaning | Effect |
| --- | --- | --- |
| trusted | appears in trusted text | none |
| untrusted | appears only in untrusted text | finding at `checks.provenance` |
| novel | appears in neither | none |

Matching is case-insensitive and whole-token: the characters around an
occurrence must not continue the value. Letters, digits, `_`, `@`, `+` and
`-` continue a value, and so does `.` when another such character follows.
So `team@acme.example` is found at the end of a sentence but not inside
`finance-team@acme.example` or `team@acme.example.org`. Numbers, and strings
that are just a number, are compared numerically, so `420`, `"420.0"`, and
`"$420.00"` agree, at any size. Other strings shorter than three characters
are never attributed.

**Why escalate rather than deny?** Because the same signal fires on
legitimate work. "Reply to the person who emailed me" has to take the
recipient from the inbox. The evaluation's `reply-to-sender` scenario shows
this: provenance flags it, and a reviewer approves it. Denying would break
that task outright. Escalating costs one review.

**Why not URLs by default?** Following a link from a page is ordinary
browsing. Fetch destinations are already constrained by the domain scope.
Add `"url"` to `roles` for stricter deployments.

**What it misses.** Values the agent derived rather than copied are
*novel*, not *untrusted*. This is the check's main limitation, and why scope
and review sit behind it.

### Irreversibility

Irreversible tools escalate by default. That's where most of the review
load in the evaluation comes from (0.75 reviews per benign task). Two ways
to lower it without losing the guarantee: narrower per-task scope, so the
escalation is about a pre-approved target, or a reviewer that auto-approves
actions matching an explicit, task-specific plan. Lowering the verdict to
`allow` is supported, and `lint-policy` warns about it.

### Protected paths

These halt the session:

- a write or delete whose path is inside a protected path, or *above* one
  (deleting `/workspace` deletes `/workspace/.airlock`);
- a command that names a protected path in any argument, including option
  values (`--out=…`, `-o…`) or a spelling that normalises to one
  (`notes/../.airlock`). As a backstop, the literal protected path appearing
  anywhere in the command also halts.

Reading protected files is allowed: the agent may need to know what its
policy is. A command that lists a parent directory is allowed too, since
listing isn't modifying. What argument inspection can't see is a program
that changes a protected file without naming it, which is why the policy
and log should also live outside the agent's reach (threat model,
assumption 3).

### Budgets and the circuit breaker

Usage counts only allowed actions. Denials have their own counter, and
rejected reviews count as denials: a stream of proposals that a person had
to turn down is the same signal as a stream the policy turned down.

## Monitors

```python
class Monitor(Protocol):
    name: str
    def assess(self, ctx: MonitorContext) -> list[Finding]: ...
```

`LLMMonitor` takes any `judge: Callable[[str], str]`, so it works with any
model or provider, or a stub in tests. It renders the task, the recent
history (tool outputs fenced in `<untrusted>` tags, with `<` and `>`
escaped so the content can't close the fence), the proposed action, and the
findings so far. It asks for `{"suspicion": 0-100, "reason": ...}`. Scores
map to allow, escalate, or deny by threshold. A judge that errors or
returns something unparseable yields `on_error` (default escalate).

Monitors run after the deterministic checks and only when those haven't
already denied. That keeps cost down, and it means a monitor can never be
the reason something forbidden runs.

## Review

```python
class Reviewer(Protocol):
    def review(self, request: ReviewRequest) -> Review: ...
```

Bundled: `ConsoleReviewer` (anything but an explicit yes is a no),
`CallbackReviewer` (approves only when the callback returns exactly `True`),
and `ApproveAll` / `DenyAll` (used by the evaluation to bracket reviewer
quality). A reviewer that raises, or returns anything other than a `Review`
with a boolean answer, counts as a rejection. `ReviewRequest.render()` gives
the reviewer the task, the action, its effects and reversibility, and every
finding.

## Audit log

JSON lines, one record per event (`session_start`, `principal_message`,
`decision`, `result`, `halt`):

```json
{"seq": 4, "ts": 1760716800.0, "event": "decision", "data": {...}, "prev": "<hash of seq 3>", "hash": "<sha256 or hmac>"}
```

`hash = H(prev + "\n" + canonical_json(record without hash))`, with SHA-256,
or HMAC-SHA-256 if a key is configured. `airlock verify-log` re-walks the
chain and reports the first bad record. Each line must also be exactly the
canonical serialisation of the record it parses to, so extra text that a
JSON parser would quietly drop can't ride along on a valid hash. Records are
ASCII-escaped, so any string an agent produces can be logged. Opening an
existing log verifies it first and refuses to append to a broken one. If a
decision can't be written, the session halts: an action that can't be
audited doesn't run.

What it detects: edits, deletions, and reorders inside the chain. With a
key, it also detects recomputing the chain without the key. What it doesn't
detect: truncation at the tail. That's why `AuditLog.head` exists, so you
can publish it elsewhere.

Tool outputs are logged as SHA-256 plus length unless `log_outputs=True`,
so the log doesn't also become a copy of everything the agent read.
Arguments are logged in full, because they're the decision being audited.
That includes message bodies and file contents, so treat the log as
sensitive.

## Integration

Three ways to put the gateway in a loop, from least to most code:

```python
tools = session.guard({"read_file": read_file, ...})   # raises ActionBlocked
session.call(tools, "read_file", path="...")            # same, one call
decision = session.check(action)                         # full control
if decision.allowed:
    session.record_result(decision, run(action))
```

[`examples/claude_agent.py`](../examples/claude_agent.py) uses the last form
inside a Claude tool-use loop. Blocked calls go back to the model as error
tool results, carrying the reasons, so it can adjust.

## Deliberate omissions

- **No content inspection.** airlock decides where data may go and which
  actions may happen. It doesn't read message bodies. Mixing the two makes
  both worse, and content inspection is a separate, well-served problem.
- **No runtime dependencies.** The trusted base should be small enough to
  read. It's about 1,800 lines of standard-library Python, CLI included.
- **No async API.** Checks are cheap and synchronous. A slow LLM monitor is
  the exception, and it can be wrapped.
