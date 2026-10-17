"""Least-privilege scope: what a single task is allowed to touch.

Every matcher here normalises its input before comparing, and every one
answers "no" when it cannot parse what it was given.
"""

from __future__ import annotations

import fnmatch
import math
import posixpath
import re
import shlex
from dataclasses import dataclass, replace
from email.utils import parseaddr
from urllib.parse import urlsplit

_SHELL_SYNTAX = frozenset(";&|<>`$\n\r")
_GLOB = frozenset("*?[")
_LABEL = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)")


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

    def __post_init__(self) -> None:
        if not isinstance(self.cwd, str) or not self.cwd.startswith("/"):
            raise ValueError(f"scope cwd must be an absolute path, got {self.cwd!r}")

    def exceeds(self, ceiling: Scope) -> list[str]:
        """List every grant in this scope that ``ceiling`` does not also grant."""
        problems: list[str] = []
        for path in self.read_paths:
            if not _grant_within(path, self.cwd, ceiling.read_paths, ceiling.cwd):
                problems.append(f"read path {path!r}")
        for path in self.write_paths:
            if not _grant_within(path, self.cwd, ceiling.write_paths, ceiling.cwd):
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


def _is_glob(pattern: str) -> bool:
    return any(ch in _GLOB for ch in pattern)


def path_matches(path: str, patterns: tuple[str, ...], cwd: str = "/") -> str | None:
    """Return the first pattern that covers ``path``.

    A pattern with ``*``, ``?`` or ``[`` is a glob (``*`` also crosses ``/``);
    anything else covers that path and everything below it. Relative
    patterns resolve against ``cwd``.
    """
    for pattern in patterns:
        resolved = normalize_path(pattern, cwd)
        if _is_glob(resolved):
            if fnmatch.fnmatchcase(path, resolved):
                return pattern
        elif path_within(path, resolved):
            return pattern
    return None


def _grant_within(entry: str, cwd: str, ceiling: tuple[str, ...], ceiling_cwd: str) -> bool:
    """True only if every path ``entry`` could match is also covered by ``ceiling``.

    A glob is accepted if the ceiling has the identical glob, or if everything
    it can match lies under a plain directory in the ceiling. A plain entry
    must lie under a plain ceiling directory: a glob ceiling cannot vouch for
    the subtree below a name it happens to match.
    """
    resolved = normalize_path(entry, cwd)
    roots = [normalize_path(c, ceiling_cwd) for c in ceiling]
    plain = [r for r in roots if not _is_glob(r)]
    if not _is_glob(resolved):
        return any(path_within(resolved, r) for r in plain)
    if resolved in roots:
        return True
    literal = resolved[: min(resolved.index(ch) for ch in _GLOB if ch in resolved)]
    base = normalize_path(literal[: literal.rfind("/") + 1] or "/")
    return any(path_within(base, r) for r in plain)


def command_path_args(argv: list[str]) -> list[str]:
    """Arguments of a command that may name a path, including ``--opt=PATH`` and ``-oPATH``.

    Positional arguments are all treated as paths, since only the program knows
    which ones are. Option values are treated as paths when they look like one.
    """
    found = []
    for token in argv[1:]:
        if token.startswith("-"):
            value = "" if token.startswith("--") else token[2:]  # -oPATH
            if "=" in token:
                value = token.split("=", 1)[1]  # --opt=PATH, -Dkey=PATH
            if value.startswith(("/", ".", "~")) or "/" in value:
                found.append(value)
        elif "=" in token:
            found.append(token.split("=", 1)[1] or ".")
        else:
            found.append(token)
    return found


def normalize_host(host: str) -> str:
    """Return the ASCII (punycode) form of a hostname, or raise ``ValueError``.

    Non-ASCII names are accepted only if encoding is reversible. IDNA 2003
    maps some characters (``ß``, fullwidth letters) onto plain ASCII, while
    other resolvers do not, so such a name could be checked as one host and
    connect to another. Those are rejected, as is anything that is not a
    syntactically valid DNS name.
    """
    if not isinstance(host, str):
        raise ValueError("host must be a string")
    host = host.strip().rstrip(".").lower()
    if not host:
        raise ValueError("empty host")
    if not host.isascii():
        try:
            encoded = host.encode("idna")
            if encoded.decode("idna") != host:
                raise ValueError(f"ambiguous internationalised host {host!r}")
        except UnicodeError as exc:
            raise ValueError(f"invalid host {host!r}") from exc
        host = encoded.decode("ascii")
    if len(host) > 253 or not all(_LABEL.fullmatch(label) for label in host.split(".")):
        raise ValueError(f"invalid host {host!r}")
    return host


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
