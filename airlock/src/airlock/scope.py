"""Least-privilege scope: what a single task is allowed to touch.

Every matcher here normalises its input before comparing, and every one
answers "no" when it cannot parse what it was given.
"""

from __future__ import annotations

import fnmatch
import math
import posixpath
import shlex
from dataclasses import dataclass, replace
from email.utils import parseaddr
from urllib.parse import urlsplit

_SHELL_SYNTAX = frozenset(";&|<>`$\n\r")


@dataclass(frozen=True)
class Scope:
    """Resources one task may use. Empty tuples grant nothing."""

    cwd: str = "/"
    read_paths: tuple[str, ...] = ()
    write_paths: tuple[str, ...] = ()
    protected_paths: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    recipients: tuple[str, ...] = ()
    recipient_domains: tuple[str, ...] = ()
    payees: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()

    def exceeds(self, ceiling: Scope) -> list[str]:
        """List every grant in this scope that ``ceiling`` does not also grant."""
        problems: list[str] = []
        for path in self.read_paths:
            if path_matches(normalize_path(path), ceiling.read_paths) is None:
                problems.append(f"read path {path!r}")
        for path in self.write_paths:
            if path_matches(normalize_path(path), ceiling.write_paths) is None:
                problems.append(f"write path {path!r}")
        problems += [f"domain {d!r}" for d in self.domains if not host_allowed(d, ceiling.domains)]
        problems += [f"recipient {r!r}" for r in self.recipients if not recipient_allowed(r, ceiling)]
        problems += [
            f"recipient domain {d!r}"
            for d in self.recipient_domains
            if not host_allowed(d, ceiling.recipient_domains)
        ]
        problems += [f"payee {p!r}" for p in self.payees if not payee_allowed(p, ceiling)]
        problems += [f"command {c!r}" for c in self.commands if c not in ceiling.commands]
        return problems

    def with_protected(self, extra: tuple[str, ...]) -> Scope:
        merged = tuple(dict.fromkeys(extra + self.protected_paths))
        return replace(self, protected_paths=merged)


def normalize_path(path: str, cwd: str = "/") -> str:
    """Resolve ``path`` against ``cwd`` and collapse ``.``/``..`` lexically."""
    if not isinstance(path, str) or not path or "\x00" in path:
        raise ValueError(f"invalid path {path!r}")
    joined = path if path.startswith("/") else posixpath.join(cwd, path)
    normalized = posixpath.normpath(joined)
    # normpath keeps a leading "//" (POSIX allows it to be special); we do not.
    return "/" + normalized.lstrip("/")


def path_within(path: str, root: str) -> bool:
    root = root.rstrip("/") or "/"
    if root == "/":
        return path.startswith("/")
    return path == root or path.startswith(root + "/")


def path_matches(path: str, patterns: tuple[str, ...]) -> str | None:
    """Return the first pattern that covers ``path``: a glob, or a directory prefix."""
    for pattern in patterns:
        if any(ch in pattern for ch in "*?["):
            if fnmatch.fnmatchcase(path, pattern):
                return pattern
        elif path_within(path, normalize_path(pattern)):
            return pattern
    return None


def normalize_host(host: str) -> str:
    """Lowercase and IDNA-encode, so a non-ASCII lookalike never equals an ASCII name."""
    host = host.strip().rstrip(".").lower()
    if not host:
        raise ValueError("empty host")
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError(f"invalid host {host!r}") from exc


def host_allowed(host: str, allowed: tuple[str, ...]) -> bool:
    """Exact match or a true subdomain of an allowed name. Never a suffix match."""
    try:
        host = normalize_host(host)
    except ValueError:
        return False
    for entry in allowed:
        try:
            name = normalize_host(entry)
        except ValueError:
            continue
        if host == name or host.endswith("." + name):
            return True
    return False


def url_host(url: str) -> str:
    """Return the host a URL actually connects to. Raises ``ValueError`` if unusable."""
    if not isinstance(url, str):
        raise ValueError("url must be a string")
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"unsupported scheme {parts.scheme!r}")
    if parts.username is not None or parts.password is not None:
        raise ValueError("credentials in URLs are not allowed")
    if not parts.hostname:
        raise ValueError("url has no host")
    return normalize_host(parts.hostname)


def parse_recipient(value: str) -> tuple[str, str]:
    """Return ``(address, domain)`` for a single email address."""
    if not isinstance(value, str) or "," in value or ";" in value:
        raise ValueError("expected exactly one recipient")
    _, address = parseaddr(value)
    if address.count("@") != 1:
        raise ValueError(f"not an email address: {value!r}")
    local, domain = address.rsplit("@", 1)
    if not local or not domain:
        raise ValueError(f"not an email address: {value!r}")
    domain = normalize_host(domain)
    return f"{local.lower()}@{domain}", domain


def recipient_allowed(value: str, scope: Scope) -> bool:
    try:
        address, domain = parse_recipient(value)
    except ValueError:
        return False
    allowed = set()
    for entry in scope.recipients:
        try:
            allowed.add(parse_recipient(entry)[0])
        except ValueError:
            continue
    return address in allowed or host_allowed(domain, scope.recipient_domains)


def payee_allowed(value: str, scope: Scope) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().casefold() in {p.strip().casefold() for p in scope.payees}


def parse_amount(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("amount must be a number")
    try:
        amount = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"amount must be a number, got {value!r}") from exc
    if not math.isfinite(amount) or amount < 0:
        raise ValueError(f"amount must be finite and non-negative, got {value!r}")
    return amount


def parse_command(value: str) -> list[str]:
    """Split a command for shell-free execution. Any shell syntax is rejected outright."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("empty command")
    if any(ch in _SHELL_SYNTAX for ch in value):
        raise ValueError("shell syntax is not allowed; commands run without a shell")
    try:
        argv = shlex.split(value)
    except ValueError as exc:
        raise ValueError(f"unparseable command: {exc}") from exc
    if not argv:
        raise ValueError("empty command")
    return argv


def command_allowed(value: str, scope: Scope) -> bool:
    try:
        argv = parse_command(value)
    except ValueError:
        return False
    return argv[0] in scope.commands
