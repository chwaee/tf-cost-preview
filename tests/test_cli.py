"""CLI exit codes and stdout."""

import json
from pathlib import Path

import pytest
from tf_cost.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
MINIMAL = FIXTURES / "minimal_plan.json"


def test_file_path_writes_a_table(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([str(MINIMAL)])
    captured = capsys.readouterr()
    assert code == 0
    assert "TOTAL ESTIMATE:" in captured.out
    assert "$7.59" in captured.out
    assert captured.err == ""


def test_stdin_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.stdin", _stdin(MINIMAL))
    code = main(["--format", "json", "-"])
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "1.0"
    assert payload["resources"][0]["monthly_estimate"] == 7.59


def test_currency_case_is_ignored(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--currency", "usd", str(MINIMAL)]) == 0
    capsys.readouterr()


def test_unsupported_currency(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--currency", "EUR", str(MINIMAL)])
    captured = capsys.readouterr()
    assert code == 2
    assert "USD" in captured.err
    assert captured.out == ""


def test_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["/tmp/does-not-exist-tf-cost.json"])
    captured = capsys.readouterr()
    assert code == 2
    assert "not found" in captured.err


def test_bad_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{", encoding="utf-8")
    code = main([str(plan)])
    captured = capsys.readouterr()
    assert code == 2
    assert "not valid JSON" in captured.err


def test_tty_without_a_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", _stdin(MINIMAL, tty=True))
    code = main([])
    captured = capsys.readouterr()
    assert code == 2
    assert "pipe" in captured.err


def test_help_lists_examples(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--help"])
    captured = capsys.readouterr()
    assert code == 0
    assert "tf-cost --format json" in captured.out
    assert "HarderAWS" in captured.out
    assert "terraform show -json" in captured.out


class _Stdin:
    def __init__(self, text: str, *, tty: bool) -> None:
        self._text = text
        self._tty = tty

    def read(self) -> str:
        return self._text

    def isatty(self) -> bool:
        return self._tty


def _stdin(path: Path, *, tty: bool = False) -> _Stdin:
    return _Stdin(path.read_text(encoding="utf-8"), tty=tty)
