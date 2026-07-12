# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-07-12

### Added

- Cross-platform `lego-lookup` command-line application for Python 3.10 and newer.
- Paginated Rebrickable set inventory downloading and offline per-user caching.
- Continuous interactive lookup and one-off element lookup commands.
- Alternate element ID matching using the filename in a part image URL.
- Official LEGO external colour code and colour name extraction, with sensible fallbacks.
- Automatic clipboard copying through `pbcopy` on macOS, `clip` on Windows, and
  `wl-copy`, `xclip`, or `xsel` on Linux.
- Guided setup scripts for macOS, Windows, and Linux.
- GitHub Actions test matrix covering Python 3.10–3.13 on macOS, Windows, and Linux.

[Unreleased]: https://github.com/MES30004E/lego-element-lookup/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/MES30004E/lego-element-lookup/releases/tag/v1.0.0
