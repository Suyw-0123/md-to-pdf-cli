"""Unit tests for the Chromium auto-install / launch fallback in pdf_render."""

from __future__ import annotations

import pytest
from playwright.sync_api import Error as PlaywrightError

from md2pdf import pdf_render
from md2pdf.pdf_render import BrowserNotInstalledError

_MISSING_MSG = "Executable doesn't exist at /home/u/.cache/ms-playwright/chromium"


class _FakeChromium:
    """Stand-in for ``playwright.chromium`` that fails until 'installed'."""

    def __init__(self, fail_times: int):
        self._remaining_failures = fail_times
        self.launch_calls = 0

    def launch(self, args=None):
        self.launch_calls += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise PlaywrightError(_MISSING_MSG)
        return "browser"


class _FakePlaywright:
    def __init__(self, chromium: _FakeChromium):
        self.chromium = chromium


def test_auto_install_enabled_default(monkeypatch):
    monkeypatch.delenv(pdf_render._AUTO_INSTALL_ENV, raising=False)
    assert pdf_render._auto_install_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "", "  False  "])
def test_auto_install_can_be_disabled(monkeypatch, value):
    monkeypatch.setenv(pdf_render._AUTO_INSTALL_ENV, value)
    assert pdf_render._auto_install_enabled() is False


def test_chromium_launch_args_default_empty(monkeypatch):
    monkeypatch.delenv(pdf_render._NO_SANDBOX_ENV, raising=False)
    assert pdf_render._chromium_launch_args() == []


@pytest.mark.parametrize("value", ["1", "true", "YES", "on"])
def test_chromium_launch_args_no_sandbox(monkeypatch, value):
    monkeypatch.setenv(pdf_render._NO_SANDBOX_ENV, value)
    assert pdf_render._chromium_launch_args() == ["--no-sandbox", "--disable-dev-shm-usage"]


def test_is_missing_browser_error_only_matches_install_errors():
    assert pdf_render._is_missing_browser_error(PlaywrightError(_MISSING_MSG))
    assert not pdf_render._is_missing_browser_error(PlaywrightError("Timeout 30000ms"))


def test_launch_installs_then_retries(monkeypatch):
    chromium = _FakeChromium(fail_times=1)
    installed: list[bool] = []

    def fake_install() -> bool:
        installed.append(True)
        return True

    monkeypatch.setattr(pdf_render, "_install_chromium", fake_install)

    result = pdf_render._launch_chromium(_FakePlaywright(chromium))

    assert result == "browser"
    assert installed == [True]  # auto-install attempted exactly once
    assert chromium.launch_calls == 2  # initial failure + successful retry


def test_launch_raises_when_install_fails(monkeypatch):
    chromium = _FakeChromium(fail_times=2)
    monkeypatch.setattr(pdf_render, "_install_chromium", lambda: False)

    with pytest.raises(BrowserNotInstalledError):
        pdf_render._launch_chromium(_FakePlaywright(chromium))


def test_launch_skips_install_when_disabled(monkeypatch):
    chromium = _FakeChromium(fail_times=1)

    def fail_if_called() -> bool:  # pragma: no cover - must not run
        raise AssertionError("auto-install should be skipped")

    monkeypatch.setenv(pdf_render._AUTO_INSTALL_ENV, "0")
    monkeypatch.setattr(pdf_render, "_install_chromium", fail_if_called)

    with pytest.raises(BrowserNotInstalledError):
        pdf_render._launch_chromium(_FakePlaywright(chromium))


def test_launch_reraises_unrelated_errors(monkeypatch):
    class _BoomChromium:
        def launch(self, args=None):
            raise PlaywrightError("Timeout 30000ms exceeded")

    def fail_if_called() -> bool:  # pragma: no cover - must not run
        raise AssertionError("auto-install should not run for unrelated errors")

    monkeypatch.setattr(pdf_render, "_install_chromium", fail_if_called)

    with pytest.raises(PlaywrightError):
        pdf_render._launch_chromium(_FakePlaywright(_BoomChromium()))
