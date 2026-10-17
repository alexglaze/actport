"""A real Claude tool-use loop with airlock in the middle.

Every tool call Claude makes goes through ``Session.check`` before it runs.
Escalations are asked on the terminal, and a second model call acts as a
monitor. The tools operate on the simulated workspace from the evaluation
suite, so nothing touches your machine.

    pip install anthropic
    python examples/claude_agent.py "Summarise the notes in /workspace/notes into /workspace/out/summary.md"

This uses a hand-written loop rather than the SDK's tool runner so that the
gate, the result bookkeeping, and the audit trail are all visible in one place.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

import anthropic
from anthropic.types.beta import BetaMessageParam, BetaToolParam

from airlock import Action, Airlock, ConsoleReviewer, LLMMonitor, Verdict, default_policy
from airlock.evals import World
from airlock.evals.scenarios import NOTES

AGENT_MODEL = "claude-opus-5-5"
# A separate model call keeps the monitor out of the agent's context. A smaller
# model is a common choice here; set it to whatever you trust.
MONITOR_MODEL = "claude-opus-5-5"
# On a safety-classifier decline, the API retries on its recommended fallback model.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM = (
    "You are a careful assistant working in a sandboxed workspace rooted at /workspace. "
    "Use the tools to complete the user's task. Some tool calls are checked by a policy "
    "gateway; if one is blocked, read the reason and adjust, or explain why you cannot finish."
)


def _tool(name: str, description: str, **props: str) -> BetaToolParam:
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": list(props),
            "additionalProperties": False,
        },
    }


TOOLS = [
    _tool("list_dir", "List the entries of a directory.", path="Absolute directory path"),
    _tool("read_file", "Read a text file.", path="Absolute file path"),
    _tool("write_file", "Write a text file.", path="Absolute file path", content="File contents"),
    _tool(
        "send_email",
        "Send an email.",
        to="One recipient address",
        subject="Subject line",
        body="Message body",
    ),
]


def _text(response: Any) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


def _echoable(content: list[Any]) -> list[Any]:
    """After a server-side fallback, drop non-text blocks from before the last fallback marker."""
    marks = [i for i, block in enumerate(content) if block.type == "fallback"]
    if not marks:
        return content
    cut = marks[-1]
    return [b for b in content[:cut] if b.type == "text"] + content[cut:]


def make_judge(client: anthropic.Anthropic) -> Callable[[str], str]:
    def judge(prompt: str) -> str:
        response = client.beta.messages.create(
            model=MONITOR_MODEL,
            max_tokens=1024,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": prompt}],
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("monitor model declined")
        return _text(response)

    return judge


def run(task: str) -> None:
    client = anthropic.Anthropic()
    world = World(files=dict(NOTES))
    airlock = Airlock(
        default_policy(),
        reviewer=ConsoleReviewer(),
        monitors=[LLMMonitor(make_judge(client))],
    )
    session = airlock.session(task)
    messages: list[BetaMessageParam] = [{"role": "user", "content": task}]

    for _ in range(25):
        response = client.beta.messages.create(
            model=AGENT_MODEL,
            max_tokens=16000,
            system=SYSTEM,
            tools=TOOLS,
            output_config={"effort": "high"},
            messages=messages,
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            print("The model declined this request.")
            return
        messages.append({"role": "assistant", "content": _echoable(response.content)})
        if response.stop_reason != "tool_use":
            print(_text(response))
            break

        results: list[Any] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            decision = session.check(Action(block.name, dict(block.input)))
            print(decision.explain())
            if decision.allowed:
                try:
                    output = str(world.tools()[block.name](**block.input))
                    session.record_result(decision, output)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
                except Exception as exc:  # noqa: BLE001 - report tool errors back to the model
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(exc),
                            "is_error": True,
                        }
                    )
            else:
                reasons = "; ".join(f.message for f in decision.findings if f.verdict > Verdict.ALLOW)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Blocked by policy ({decision.verdict}): {reasons}",
                        "is_error": True,
                    }
                )
        messages.append({"role": "user", "content": results})
        if session.halted:
            print("Session halted by the gateway.")
            break

    print("\nWorkspace writes:", json.dumps(world.writes))
    print("Emails sent:", json.dumps([m["to"] for m in world.sent]))


if __name__ == "__main__":
    run(" ".join(sys.argv[1:]) or "Summarise the notes in /workspace/notes into /workspace/out/summary.md.")
