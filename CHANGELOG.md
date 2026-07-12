# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Asynchronously cached Rebrickable part thumbnails in the desktop result card, with
  safe offline placeholders and bounded image validation.

### Changed

- Polished the desktop result layout and centred the studs in generated application icons.

## [1.2.0] - 2026-07-12

### Added

- Tkinter desktop edition with a guided first-run wizard and persistent lookup window.
- Operating-system keychain storage for Rebrickable API keys, with a session-only fallback.
- Native PyInstaller packaging definitions for macOS, Windows, and Linux release assets.
- Background inventory downloads, set management, settings, and visible clipboard confirmation.

### Security

- Strict HTTPS pagination validation, bounded responses, sanitised download errors, and stronger cache validation.

## [1.1.0] - 2026-07-12

### Added

- Bare numerical element IDs such as `lego-lookup 6212040` as shorthand for the
  backwards-compatible `lego-lookup lookup 6212040` command.
- Cached RGB colour swatches with ANSI true-colour output, plain-text fallbacks,
  `NO_COLOR` support, and a `--no-colour` option.
- Persistent interactive mode with repeated offline lookups, automatic clipboard
  copying, input recovery, and clean quit, interrupt, and EOF handling.

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

[Unreleased]: https://github.com/MES30004E/lego-element-lookup/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/MES30004E/lego-element-lookup/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/MES30004E/lego-element-lookup/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/MES30004E/lego-element-lookup/releases/tag/v1.0.0
