"""Tamper-evident audit log: append-only JSON lines, each record hash-chained to the last.

Without a key this detects accidental corruption and naive edits, but anyone
who can write the file can recompute the whole chain. With a key (HMAC), a
forger also needs the key, so keep it somewhere the agent cannot read.
Either way, anchoring the latest hash somewhere else (a ticket, a commit)
pins the history up to that point.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def _digest(prev: str, body: Mapping[str, Any], key: bytes | None) -> str:
    payload = prev.encode() + b"\n" + _canonical(body)
    if key is None:
        return hashlib.sha256(payload).hexdigest()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


class AuditLog:
    """Writes to ``path`` if given, and always keeps records in memory."""

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        key: bytes | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self._key = key
        self._clock = clock
        self.records: list[dict[str, Any]] = []
        self._seq = 0
        self._head = GENESIS
        if self.path is not None and self.path.exists() and self.path.stat().st_size > 0:
            result = verify(self.path, key=key)
            if not result.ok:
                raise ValueError(f"refusing to append to a broken audit log: {result.error}")
            self._seq = result.count
            self._head = result.head

    @property
    def head(self) -> str:
        """Hash of the latest record. Publish it elsewhere to pin history."""
        return self._head

    def append(self, event: str, data: Mapping[str, Any]) -> dict[str, Any]:
        body = {
            "seq": self._seq + 1,
            "ts": self._clock(),
            "event": event,
            "data": dict(data),
            "prev": self._head,
        }
        # Round-trip so the stored record is exactly what verify() will re-hash.
        body = json.loads(_canonical(body))
        record = {**body, "hash": _digest(self._head, body, self._key)}
        if self.path is not None:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        self.records.append(record)
        self._seq += 1
        self._head = record["hash"]
        return record


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    count: int
    head: str
    error: str = ""


def verify(path: str | Path, *, key: bytes | None = None) -> VerifyResult:
    """Re-walk the chain. Reports the first record that does not check out."""
    prev = GENESIS
    count = 0
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                return VerifyResult(False, count, prev, f"line {lineno}: blank line")
            try:
                record = json.loads(line)
                claimed = record.pop("hash")
            except (json.JSONDecodeError, KeyError, AttributeError, TypeError):
                return VerifyResult(False, count, prev, f"line {lineno}: not a valid record")
            if record.get("seq") != count + 1:
                return VerifyResult(False, count, prev, f"line {lineno}: sequence gap or reorder")
            if record.get("prev") != prev:
                return VerifyResult(False, count, prev, f"line {lineno}: chain broken (prev mismatch)")
            if not hmac.compare_digest(_digest(prev, record, key), str(claimed)):
                return VerifyResult(False, count, prev, f"line {lineno}: hash mismatch (record altered)")
            prev = str(claimed)
            count += 1
    return VerifyResult(True, count, prev)
