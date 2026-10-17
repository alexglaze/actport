# airlock

A policy gateway between a tool-using AI agent and the tools it calls.

Every action the agent proposes is checked against a declared policy before
it runs. Irreversible actions go to a person, any attempt to modify the
agent's own oversight ends the session, and every step lands in a
tamper-evident log. It is built on the assumption that the model proposing
the action can't be fully trusted: it reads text it didn't choose, it makes
mistakes, and nobody can yet verify its goals from the outside.

**The project lives in [`airlock/`](airlock/):** code, tests, docs, and the
evaluation suite.

- [What guardrails tool-using agents need](airlock/docs/position.md): the argument, including what a library can't provide
- [Threat model](airlock/docs/threat-model.md)
- [Design](airlock/docs/design.md)
- [Evaluation](airlock/docs/evaluation.md) and [full results](airlock/docs/results.md)

The evaluation runs 23 scripted scenarios without the gateway, with a
reviewer who approves exactly what the principal wanted, with one who
approves everything, and with none. With a good reviewer, none of the 15
out-of-policy actions run and all 8 ordinary tasks complete. With a
rubber-stamp reviewer, 3 get through, and they are exactly the 3 whose only
defence was review. That last number is the one that says how much of the
safety rests on a person's attention.

```bash
cd airlock
pip install -e ".[dev]"
pytest
python -m airlock eval
```

Built with [Claude Code](https://claude.com/claude-code).

## Also in this repository

The rest of the root is the source for my acting portfolio site (Next.js,
deployed on Vercel). Notes for editing it are in
[content/README.md](content/README.md).
