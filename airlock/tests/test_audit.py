import json
from pathlib import Path

import pytest

from airlock import AuditLog, verify


def make_log(path: Path, n: int = 3, key: bytes | None = None) -> AuditLog:
    clock = iter(range(1000, 2000))
    log = AuditLog(path, key=key, clock=lambda: float(next(clock)))
    for i in range(n):
        log.append("decision", {"step": i + 1, "args": {"path": f"/workspace/{i}"}})
    return log


def rewrite(path: Path, fn: object) -> None:
    lines = path.read_text().splitlines()
    path.write_text("\n".join(fn(lines)) + "\n")  # type: ignore[operator]


def test_intact_log_verifies(tmp_path: Path) -> None:
    log = make_log(tmp_path / "a.jsonl")
    result = verify(tmp_path / "a.jsonl")
    assert result.ok and result.count == 3 and result.head == log.head


def test_edited_record_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    make_log(path)

    def edit(lines: list[str]) -> list[str]:
        record = json.loads(lines[1])
        record["data"]["args"]["path"] = "/elsewhere"
        lines[1] = json.dumps(record)
        return lines

    rewrite(path, edit)
    result = verify(path)
    assert not result.ok and result.count == 1 and "hash mismatch" in result.error


def test_deleted_record_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    make_log(path)
    rewrite(path, lambda lines: [lines[0], lines[2]])
    assert "sequence" in verify(path).error


def test_reordered_records_are_detected(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    make_log(path)
    rewrite(path, lambda lines: [lines[1], lines[0], lines[2]])
    assert not verify(path).ok


def test_truncation_is_only_detectable_against_an_anchored_head(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    head = make_log(path).head
    rewrite(path, lambda lines: lines[:2])
    result = verify(path)
    assert result.ok and result.head != head  # documented limitation: pin the head elsewhere


def test_hmac_key_is_required_to_verify(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    make_log(path, key=b"k1")
    assert verify(path, key=b"k1").ok
    assert not verify(path, key=b"k2").ok
    assert not verify(path).ok


def test_appending_resumes_the_chain(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    make_log(path, n=2)
    AuditLog(path).append("decision", {"step": 3})
    result = verify(path)
    assert result.ok and result.count == 3


def test_refuses_to_append_to_a_broken_log(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    make_log(path)
    rewrite(path, lambda lines: [*lines[:2], "not json"])
    with pytest.raises(ValueError, match="broken audit log"):
        AuditLog(path)


def test_non_json_values_are_stored_as_strings(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    AuditLog(path).append("result", {"value": Path("/x"), "nested": {"set": {1}}})
    assert verify(path).ok


def test_non_canonical_lines_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    make_log(path)
    # Same parsed record, extra bytes: a duplicated key the parser would silently drop.
    rewrite(path, lambda lines: [lines[0].replace('{"data"', '{"data": "x", "data"', 1), *lines[1:]])
    assert "canonical" in verify(path).error


def test_undecodable_logs_fail_verification_cleanly(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    make_log(path)
    path.write_bytes(path.read_bytes() + b"\xff\xfe\n")
    result = verify(path)
    assert not result.ok and result.count == 3


def test_lone_surrogates_are_logged_and_verify(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    AuditLog(path).append("decision", {"args": {"content": "x\ud800y"}})
    assert verify(path).ok
