# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.1] - 2026-07-15

### Fixed

- Fixed new part preview downloads failing in frozen desktop builds because bundled
  Python/OpenSSL had no usable CA certificate store.
- Added an explicit verified certificate bundle using certifi.
- Preserved full TLS certificate and hostname verification.
- Added frozen preview-fetch packaging validation.

## [1.4.0] - 2026-07-14

### Added

- Optional Rebrickable related-design data with a validated local cache, offline reuse,
  and direct-only relationship display that avoids inferred or transitive equivalence.
- A desktop multiple-match chooser that preserves all candidate details until the user
  selects the intended part.
- Rebrickable set metadata and asynchronously cached set thumbnails.
- Typed new-set downloading plus downloaded-set discovery and filtering.
- Light, Dark, and live System themes with cross-platform semantic styling.
- Transactional tabbed Settings with Apply, Save, Cancel, Restore Defaults, dirty-state
  tracking, preview-cache controls, and safe settings migration.
- An About window, native application/File/Edit/View/Help menus, redacted diagnostics,
  trusted project links, and manual update checking through GitHub Releases.
- Responsive Wide, Medium, and Narrow desktop layouts with Auto, Wide, Tall, and
  Compact window presets.
- A polished compact top command bar with shared commands and responsive overflow.
- Safe downloaded-set management that removes selected inventory caches without touching
  shared previews, relationship data, credentials, or unrelated files.
- Polished macOS DMG presentation, Windows installer metadata, Linux desktop/AppStream
  metadata, and AppImage/tarball desktop integration.

### Changed

- Reused a Keychain credential for the running session instead of repeatedly requesting it.
- Refined preview error states, asynchronous loading, and bounded preview-cache behaviour.
- Made only the result-data region scroll while the identity header, command bar, current
  set, Element ID input, and bottom status/version bar remain fixed.
- Moved manual Copy beside the selected part code while preserving automatic clipboard copying.
- Added restrained semantic success, information, warning, error, primary, destructive,
  navigation, and related-data attribution styles.
- Improved macOS trackpad scrolling, Windows/Linux wheel normalisation, long-name wrapping,
  responsive preview sizing, and Light/System-Light control contrast.
- Allowed continuous two-axis window resizing after any preset while persisting valid manual
  dimensions without changing the selected preset.
- Improved cache discovery so relationship, metadata, AppleDouble, and other non-set files
  never appear in the downloaded-set chooser.
- Made macOS DMG creation resilient to stale mounts, isolated temporary-image locks, and
  transient `hdiutil` resource-busy failures through targeted cleanup and bounded retries.
- Accepted familiar numeric LEGO set numbers such as `10334`, resolving them to canonical
  Rebrickable identifiers such as `10334-1` before download and storage.
- Refined the generated application icon with a centred red 2×2 brick, a balanced rounded
  tile, and consistent transparent padding at every packaged size.

### Fixed

- Misleading “offline” preview status.
- AppleDouble and relationship-cache files appearing as sets.
- Typed new-set downloads not being selected correctly.
- System theme not following macOS appearance live.
- Settings transaction and dirty-state behaviour.
- Repeated Keychain reads within the same process.
- Detached status/version footer.
- Broken About-window links, diagnostics copying, closing, and repeated-window handling.
- About-window input routing when opened while Settings owns the Tk grab.
- Startup failure caused by responsive layout running before the bottom status widgets existed.
- Main-window height appearing locked because the minimum height matched common preset sizes.

## [1.2.2] - 2026-07-13

### Fixed

- Made macOS DMG creation resilient to stale mounts, temporary-file locks, and
  transient `hdiutil` resource-busy failures by using isolated workspaces,
  targeted cleanup, and bounded retries.

## [1.2.1] - 2026-07-13

### Added

- Asynchronously cached Rebrickable part thumbnails in the desktop result card, with
  safe offline placeholders and bounded image validation.

### Changed

- Polished the desktop result layout and centred the studs in generated application icons.

### Fixed

- Fixed the GitHub Actions desktop release job so it checks out the repository before
  verifying the release tag and creating the draft release.

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

[Unreleased]: https://github.com/MES30004E/lego-element-lookup/compare/v1.4.1...HEAD
[1.4.1]: https://github.com/MES30004E/lego-element-lookup/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/MES30004E/lego-element-lookup/compare/v1.2.2...v1.4.0
[1.2.2]: https://github.com/MES30004E/lego-element-lookup/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/MES30004E/lego-element-lookup/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/MES30004E/lego-element-lookup/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/MES30004E/lego-element-lookup/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/MES30004E/lego-element-lookup/releases/tag/v1.0.0
