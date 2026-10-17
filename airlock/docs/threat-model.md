# Threat model

## What is being protected

1. **The principal's intent.** Actions should be the ones the person who
   gave the task asked for, or would approve if asked.
2. **Whatever the tools can reach:** files, mailboxes, accounts, money,
   systems.
3. **Oversight itself:** the policy, the audit log, and the review channel.
   If these can be altered from inside a session, nothing else here holds.

## Where bad actions come from

airlock does not try to tell these apart. It judges the proposed action, not
the reason behind it.

| Source | Example |
| --- | --- |
| Untrusted content steering the agent | A document the agent was asked to process contains a line asking for something the principal never asked for, and the agent complies. |
| Ordinary agent error | The agent misreads the task, retries a payment that already went through, or tidies up files nobody asked it to touch. |
| Goal mismatch | The agent pursues something other than the principal's goal. We can't currently rule this out from outside the model, so the design doesn't depend on ruling it out. |
| Runaway behaviour | A loop, a retry storm, or accumulating spend. |

## Trust boundaries

| Component | Trusted? | Why |
| --- | --- | --- |
| Principal (task text, later principal messages) | Yes | They are the source of authority. |
| Policy, gateway, reviewer, audit log | Yes | This is the trusted computing base. Keep it small and out of the agent's reach. |
| Tool implementations | Trusted to match their declared spec | Every check relies on declared effects and argument roles. |
| The agent (model + its loop) | **No** | See the position note: it reads untrusted text, makes mistakes, and its goals can't be verified. |
| Tool outputs | **No** (unless the tool is declared `trusted_output`) | They are data from the world, and data has no authority. |
| Model-based monitors | Partially | They are trusted to add caution, not to grant permission, because they read untrusted content too. |

## In scope

Every action that passes through `Session.check`:

- calls to unregistered tools, or with undeclared arguments,
- paths, domains, recipients, payees, and commands outside the task's scope,
- control arguments copied from untrusted content,
- irreversible actions taken without review,
- modifications to oversight (policy, audit log),
- exceeding action, per-tool, or spend budgets,
- sessions that keep proposing denied actions.

## Out of scope, and what covers it instead

| Not covered | Why | What should cover it |
| --- | --- | --- |
| Effects that bypass the gateway | A library can't stop an agent from using an unguarded channel | Sandboxing, network policy, credentials held by the gateway |
| What's *inside* a content argument | airlock governs where data goes and which actions happen, not message contents | Narrow recipient scope, review of egress, separate content inspection where required |
| Values derived from untrusted text (not copied verbatim) | Provenance only recognises verbatim copies | Scope limits still apply. Architectural separation of planning from untrusted data is the principled fix |
| Malicious or mis-declared tools | The gateway trusts declarations | Review tool specs like any security config. Run `airlock lint-policy` |
| What an allowlisted program does with its arguments | Arguments are held to read scope. The program's own writes and network use are not mediated | Allowlist programs whose side effects you accept. Sandbox the rest |
| A compromised host, gateway, or reviewer | They are the trusted base | Standard system security |
| Harm assembled from individually allowed steps | No sequence model beyond budgets and the denial breaker | Budgets bound volume. LLM monitors can look at trajectories, with their own limits |
| Audit log truncation | A hash chain can't detect lost records at its tail | Publish the head hash elsewhere (ticket, commit, log shipper) |

## Assumptions, stated plainly

1. Every effect goes through the gateway.
2. Tool declarations are accurate.
3. The policy file and audit log live where the agent can't modify them, and
   `protected_paths` covers them as a second line.
4. Reviewers see the full review request and have time to read it.
5. The audit HMAC key, if used, is not readable by the agent.

If any of these is false in a deployment, the guarantees above weaken
accordingly. That is worth writing down per deployment, not just here.
