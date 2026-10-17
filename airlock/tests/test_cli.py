import json
from pathlib import Path

import pytest

from airlock import Action, Airlock, AuditLog, default_policy
from airlock.cli import main

BUNDLED = Path(__file__).parent.parent / "src" / "airlock" / "policies" / "default.toml"


def test_eval_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["eval", "--format", "json", "--mode", "oracle", "--scenario", "path-escape"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["results"][0]["scenario"] == "path-escape"
    assert data["results"][0]["violated"] is False


def test_eval_unknown_scenario(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["eval", "--scenario", "nope"]) == 2


def test_lint_bundled_policy(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["lint-policy", "--strict", str(BUNDLED)]) == 0
    assert "0 warning(s)" in capsys.readouterr().out


def test_lint_strict_fails_on_warnings(tmp_path: Path) -> None:
    path = tmp_path / "loose.toml"
    path.write_text('[policy]\nunknown_tool = "allow"\n[tools.t]\neffects = ["read"]\n')
    assert main(["lint-policy", str(path)]) == 0
    assert main(["lint-policy", "--strict", str(path)]) == 1


def test_verify_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "audit.jsonl"
    airlock = Airlock(default_policy(), audit=AuditLog(path, key=b"secret-key"))
    airlock.session("task").check(Action("read_file", {"path": "/workspace/a"}))
    monkeypatch.setenv("AIRLOCK_KEY", "secret-key")
    assert main(["verify-log", "--key-env", "AIRLOCK_KEY", str(path)]) == 0
    monkeypatch.setenv("AIRLOCK_KEY", "wrong")
    assert main(["verify-log", "--key-env", "AIRLOCK_KEY", str(path)]) == 1
