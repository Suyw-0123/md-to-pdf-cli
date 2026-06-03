# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases up to and including `v0.1.4` are documented in the
[GitHub Releases](https://github.com/Suyw-0123/md-to-pdf-cli/releases); this file
tracks changes from the next version onward.

## [Unreleased]

## [0.1.5] - 2026-06-03

### Added
- `md2pdf install-deps` command — installs the system shared libraries Chromium
  needs on Debian/Ubuntu by wrapping `playwright install-deps` with the current
  interpreter and `sudo`, so it works under pip / uv / uv-tool / pipx installs.

### Fixed
- The "missing system libraries" hint (added in 0.1.4) suggested
  `sudo playwright install-deps` / `sudo uv tool run …`, which fail with
  `command not found` for venv and uv-tool installs because `sudo` resets `PATH`.
  The hint now points at the new `md2pdf install-deps` command, which resolves the
  interpreter by absolute path and survives `sudo`.

[Unreleased]: https://github.com/Suyw-0123/md-to-pdf-cli/compare/v0.1.5...HEAD
[0.1.5]: https://github.com/Suyw-0123/md-to-pdf-cli/compare/v0.1.4...v0.1.5
