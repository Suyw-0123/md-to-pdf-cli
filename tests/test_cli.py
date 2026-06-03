"""CLI wiring tests: the install-deps command resolves and propagates its exit code."""

from __future__ import annotations

from typer.testing import CliRunner

from md2pdf.cli import app

runner = CliRunner()


def test_install_deps_command_runs_helper_and_succeeds(monkeypatch):
    calls: list[bool] = []
    monkeypatch.setattr("md2pdf.cli.install_system_deps", lambda: calls.append(True) or 0)

    result = runner.invoke(app, ["install-deps"])

    assert result.exit_code == 0
    assert calls == [True]  # the command actually delegated to the helper


def test_install_deps_command_propagates_failure(monkeypatch):
    monkeypatch.setattr("md2pdf.cli.install_system_deps", lambda: 1)

    result = runner.invoke(app, ["install-deps"])

    assert result.exit_code == 1
