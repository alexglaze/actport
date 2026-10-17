"""A small simulated workspace for the evaluation suite: files, inbox, web, email, payments, shell.

Nothing here touches the real machine. Tools record what they did so each
scenario can inspect the end state.
"""

from __future__ import annotations

import posixpath
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..scope import normalize_path, url_host

CWD = "/workspace"


def _norm(path: str) -> str:
    return normalize_path(path, CWD)


@dataclass
class World:
    files: dict[str, str] = field(default_factory=dict)
    inbox: list[dict[str, str]] = field(default_factory=list)
    web: dict[str, str] = field(default_factory=dict)
    sent: list[dict[str, str]] = field(default_factory=list)
    payments: list[dict[str, Any]] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    fetched: list[str] = field(default_factory=list)
    chat: list[dict[str, str]] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.files = {_norm(p): c for p, c in self.files.items()}

    # -- tools -------------------------------------------------------------

    def list_dir(self, path: str) -> str:
        root = _norm(path).rstrip("/") + "/"
        children = sorted({root + p[len(root) :].split("/")[0] for p in self.files if p.startswith(root)})
        return "\n".join(children)

    def read_file(self, path: str) -> str:
        p = _norm(path)
        if p not in self.files:
            raise FileNotFoundError(p)
        return self.files[p]

    def write_file(self, path: str, content: str) -> str:
        p = _norm(path)
        self.files[p] = content
        self.writes.append(p)
        return f"wrote {len(content)} chars to {p}"

    def delete_file(self, path: str) -> str:
        p = _norm(path)
        if p not in self.files:
            raise FileNotFoundError(p)
        del self.files[p]
        self.deleted.append(p)
        return f"deleted {p}"

    def read_inbox(self) -> str:
        return "\n\n".join(f"From: {m['from']}\nSubject: {m['subject']}\n\n{m['body']}" for m in self.inbox)

    def web_fetch(self, url: str) -> str:
        url_host(url)  # reject malformed URLs the way a real client would
        self.fetched.append(url)
        return self.web.get(url, "404 Not Found")

    def send_email(self, to: str, subject: str, body: str) -> str:
        self.sent.append({"to": to, "subject": subject, "body": body})
        return f"sent to {to}"

    def pay(self, payee: str, amount: float, memo: str = "") -> str:
        self.payments.append({"payee": payee, "amount": float(amount), "memo": memo})
        return f"paid {payee} {float(amount):.2f}"

    def run_command(self, command: str) -> str:
        # Simulates a shell, including chaining, so the unguarded baseline shows its effect.
        outputs = []
        for part in command.split("&&"):
            part = part.strip()
            self.commands.append(part)
            program = part.split()[0] if part else ""
            if program == "pytest":
                outputs.append("42 passed in 1.31s")
            elif program == "ls":
                outputs.append(self.list_dir(CWD))
            else:
                outputs.append(f"ran {part}")
        return "\n".join(outputs)

    def post_to_chat(self, channel: str, text: str) -> str:
        self.chat.append({"channel": channel, "text": text})
        return f"posted to {channel}"

    def tools(self) -> dict[str, Callable[..., Any]]:
        names = [
            "list_dir",
            "read_file",
            "write_file",
            "delete_file",
            "read_inbox",
            "web_fetch",
            "send_email",
            "pay",
            "run_command",
            "post_to_chat",
        ]
        return {name: getattr(self, name) for name in names}

    # -- helpers for scenario predicates -----------------------------------

    def exists(self, path: str) -> bool:
        return _norm(path) in self.files

    def wrote(self, path: str) -> bool:
        return _norm(path) in self.writes

    def sent_to(self, address: str) -> bool:
        return any(m["to"].strip().lower() == address.lower() for m in self.sent)

    def files_under(self, path: str) -> list[str]:
        root = _norm(path).rstrip("/") + "/"
        return [p for p in self.files if p.startswith(root)]

    @staticmethod
    def basename(path: str) -> str:
        return posixpath.basename(path)
