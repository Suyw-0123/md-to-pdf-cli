"""Unit tests for the Chromium auto-install / launch fallback in pdf_render."""

from __future__ import annotations

import pytest
from playwright.sync_api import Error as PlaywrightError

from md2pdf import pdf_render
from md2pdf.pdf_render import BrowserNotInstalledError

_MISSING_MSG = "Executable doesn't exist at /home/u/.cache/ms-playwright/chromium"
# The raw glibc loader error, as it leaked through in the wild (Ubuntu 24.04).
_MISSING_DEPS_MSG = (
    "BrowserType.launch: Target page, context or browser has been closed\n"
    "chrome-headless-shell: error while loading shared libraries: libnspr4.so: "
    "cannot open shared object file: No such file or directory"
)
# Playwright's own host-deps message. Note it recommends `playwright install-deps`,
# whose substring `playwright install` ALSO matches _is_missing_browser_error —
# so deps detection must take precedence to avoid a pointless re-download.
_HOST_DEPS_MSG = (
    "Host system is missing dependencies to run browsers.\n    sudo playwright install-deps"
)
# Playwright's wrapped variant (capital M, "system" wedged in, no loader phrase):
# only the `install-deps` signal saves it from being misread as a missing browser.
_WRAPPED_DEPS_MSG = (
    "Missing system dependencies required to run browser chromium. "
    "Install them with: sudo npx playwright install-deps chromium"
)


class _DepsBrokenChromium:
    """Browser is installed but the OS lacks the shared libs to launch it."""

    def __init__(self):
        self.launch_calls = 0

    def launch(self, args=None):
        self.launch_calls += 1
        raise PlaywrightError(_MISSING_DEPS_MSG)


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


@pytest.mark.parametrize("msg", [_MISSING_DEPS_MSG, _HOST_DEPS_MSG, _WRAPPED_DEPS_MSG])
def test_is_missing_deps_error_matches_all_playwright_wordings(msg):
    assert pdf_render._is_missing_deps_error(PlaywrightError(msg))


def test_is_missing_deps_error_ignores_unrelated_errors():
    assert not pdf_render._is_missing_deps_error(PlaywrightError(_MISSING_MSG))
    assert not pdf_render._is_missing_deps_error(PlaywrightError("Timeout 30000ms"))


@pytest.mark.parametrize("msg", [_HOST_DEPS_MSG, _WRAPPED_DEPS_MSG])
def test_host_deps_message_classified_as_deps_not_browser(monkeypatch, msg):
    """A host-deps message also matches the browser pattern; deps must win."""
    # Sanity: it really would trip the browser matcher if checked first.
    assert pdf_render._is_missing_browser_error(PlaywrightError(msg))

    class _Chromium:
        def launch(self, args=None):
            raise PlaywrightError(msg)

    def fail_if_called() -> bool:  # pragma: no cover - must not run
        raise AssertionError("must not re-download for a host-deps failure")

    monkeypatch.setattr(pdf_render, "_install_chromium", fail_if_called)

    with pytest.raises(BrowserNotInstalledError, match="install-deps"):
        pdf_render._launch_chromium(_FakePlaywright(_Chromium()))


def test_launch_reports_missing_deps_without_installing(monkeypatch):
    """Browser present but libs missing: don't download, point at install-deps."""
    chromium = _DepsBrokenChromium()

    def fail_if_called() -> bool:  # pragma: no cover - must not run
        raise AssertionError("auto-install should not run when the browser is present")

    monkeypatch.setattr(pdf_render, "_install_chromium", fail_if_called)

    with pytest.raises(BrowserNotInstalledError, match="install-deps"):
        pdf_render._launch_chromium(_FakePlaywright(chromium))

    assert chromium.launch_calls == 1  # no pointless retry


def test_launch_reports_missing_deps_after_successful_download(monkeypatch):
    """Download succeeds but the retry dies for lack of system libs."""

    class _InstallsThenDepsFail:
        def __init__(self):
            self.launch_calls = 0

        def launch(self, args=None):
            self.launch_calls += 1
            if self.launch_calls == 1:
                raise PlaywrightError(_MISSING_MSG)  # first: browser missing
            raise PlaywrightError(_MISSING_DEPS_MSG)  # retry: libs missing

    chromium = _InstallsThenDepsFail()
    monkeypatch.setattr(pdf_render, "_install_chromium", lambda: True)

    with pytest.raises(BrowserNotInstalledError, match="install-deps"):
        pdf_render._launch_chromium(_FakePlaywright(chromium))

    assert chromium.launch_calls == 2  # initial miss + retry that hit the lib error


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
