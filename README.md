# LEGO Element Lookup

[![Tests](https://github.com/MES30004E/lego-element-lookup/actions/workflows/tests.yml/badge.svg)](https://github.com/MES30004E/lego-element-lookup/actions/workflows/tests.yml)

LEGO Element Lookup is a cross-platform desktop application for identifying LEGO parts from the element IDs printed in instruction manuals. It is designed for builders who need to translate those IDs quickly when recreating sets in tools such as Mecabricks.

Enter an element ID and the app finds the matching part code, official LEGO colour code, part and colour names, inventory quantity, preview image, and source-backed related designs. It can automatically copy the part code for fast use in other tools.

After a set inventory has been downloaded, lookups work offline on macOS, Windows, and Linux. Native desktop builds are available from GitHub Releases, and a supported command-line interface is included for scripting and terminal workflows.

## Requirements

- Python 3.10 or newer
- A free Rebrickable account and API key for downloading inventories
- Internet access only while downloading or updating a set
- On Linux, `wl-copy`, `xclip`, or `xsel` for automatic clipboard copying

The downloadable desktop edition bundles Python. End users do not need to install Python or use Terminal. Source installations use the lightweight `keyring` package for secure desktop credential storage.

## Desktop application

Download the appropriate v1.4.0 release asset:

- macOS Apple Silicon: `LEGO-Element-Lookup-v1.4.0-macOS-arm64.dmg`
- macOS Intel: `LEGO-Element-Lookup-v1.4.0-macOS-x86_64.dmg`
- Windows 10/11: `LEGO-Element-Lookup-v1.4.0-Windows-x86_64-Setup.exe`
- Linux AppImage: `LEGO-Element-Lookup-v1.4.0-Linux-x86_64.AppImage`
- Linux tarball fallback: `LEGO-Element-Lookup-v1.4.0-Linux-x86_64.tar.gz`

On macOS, open the DMG and drag **LEGO Element Lookup** to the **Applications** shortcut shown in its installation window. The DMG contains only the app, the Applications shortcut, and its project-owned installation artwork. The Intel and Apple Silicon images use the same layout.

The Windows installer is a per-user installation: it adds a Start Menu entry, offers an optional desktop shortcut and an optional launch after interactive setup, and leaves your configuration and downloaded caches intact during upgrades or uninstall. It never launches the app during a silent install.

On Linux, the AppImage ships a reverse-DNS desktop entry, AppStream metadata, and hicolor icons for desktop integration. Make it executable before starting it. The `.tar.gz` remains available as a fallback for systems where AppImage or FUSE is unavailable.

On first launch, the setup wizard asks for your Rebrickable API key, default set, and cache location. The key is saved in the operating system keychain when available and is never included in the application. If secure storage is unavailable, the wizard can retain it only for the current session. After the inventory downloads, lookups work offline.

The main window accepts repeated element IDs, shows a cached thumbnail of the LEGO part alongside its part and colour information, renders the cached RGB swatch, and automatically copies the part code. When one element ID has multiple inventory matches, the desktop app asks you to choose the part before copying it. Part and set thumbnails load asynchronously from Rebrickable the first time they are viewed and are then retained in the local cache. Offline lookups remain available even when a preview has not yet been cached. A preview can explicitly be loading, cached, not cached, unavailable offline, timed out, rejected as untrusted, or invalid—network failures are not misleadingly labelled as offline.

The desktop window uses responsive breakpoints rather than continuously shrinking text. At wide and medium sizes the result keeps its two-column preview/detail layout; below 760 pixels it stacks the preview above the details and moves secondary commands into an overflow menu. Only the match and result-data region scrolls: the identity header, compact command bar, current set, Element ID input, and status/version bar remain fixed. Status messages use restrained semantic accents for success, progress, warnings, and errors. The main window resizes freely in both axes down to 640 × 560 pixels, while Settings remains usable down to 720 × 600 pixels. Resizing reuses decoded preview images and never initiates network requests.

Settings are organised into General, Lookup, Images and cache, Data, and Account and security tabs. Choose a System, Light, or Dark theme, comfortable or compact density, and an Auto, Wide, Tall, or Compact starting-window layout; manual resizing always remains available, and Auto restores the last valid manual size. Configure automatic copying and optional details, and control previews. On macOS, System follows Light/Dark appearance changes while the application is running using a lightweight, bounded monitor; manual Light or Dark remains fixed. The preview cache contains only part preview images and metadata, reports its size, can be cleared independently, and may use an oldest-first size limit (250 MB by default) or no automatic eviction. Downloaded-set selection remains available from the main window, and a valid new set number is downloaded before it becomes active. API keys never enter these settings or the preview cache.

The native application menu provides About, Settings, and Check for Updates, with **Command+,** opening Settings on macOS. File, Edit, View, and Help menus expose the same change-set, update, cache-folder, copy, input-focus, window-layout, repository, and support actions used by the visible controls. The About window shows the installed version and can copy path-free, secret-free runtime diagnostics. **Check for updates** opens the project’s trusted GitHub Releases page; it does not download, install, replace, or downgrade the application. Automatic background checks and stable/beta update delivery remain reserved for a later signed-update design.

The desktop app reads a stored API key once per running session and reuses the in-memory value for inventory operations. Stable releases are intended to keep a consistent application identity. Unsigned or ad-hoc development rebuilds may ask for Keychain access again because their code identity can change, so choosing **Always Allow** is not guaranteed to persist across rebuilt development apps; this does not weaken or bypass Keychain security.

Touch ID protection is deferred as a possible future macOS-only enhancement. Any implementation would use optional Keychain user-presence protection, use Touch ID when available with a password fallback, require no administrator access, and leave Windows and Linux functionality unchanged.

Native macOS vibrancy or translucency is deferred as an optional future experiment. The solid ttk theme remains the cross-platform default and fallback; any future implementation must be macOS-only when supported, require no privacy or administrator permissions, add no required dependency, and have no effect on Windows or Linux.

Related-design data is optional and downloaded separately from Rebrickable's structured catalogue data; it is never bundled with the application or release archives. The app shows only direct, source-backed relationships and labels them as alternate designs, mould variants, decorated variants, or related components; it does not claim that related parts are interchangeable or transitively equivalent. Cached relationship data and set thumbnails remain available offline. MOC and Mecabricks project support is not included.

### Unsigned beta warnings

Early desktop releases are unsigned:

- **macOS:** Gatekeeper may report an unidentified developer. In System Settings, open **Privacy & Security** and approve this specific application. Do not disable Gatekeeper globally.
- **Windows:** SmartScreen may show an Unknown Publisher warning. Confirm the filename and compare it with `SHA256SUMS.txt` before choosing **Run anyway**.
- **Linux:** make the AppImage executable in file properties if necessary. Some systems require FUSE; use the `.tar.gz` fallback when AppImage cannot start.

LEGO is a trademark of the LEGO Group. LEGO Element Lookup is an independent project and is not affiliated with or endorsed by the LEGO Group. Inventory, relationship, metadata, and image URLs are obtained from [Rebrickable](https://rebrickable.com/) at the user's request and remain subject to its terms.

Always verify the release checksum before bypassing an operating-system warning.

## Quick start

Clone or download this repository, open a terminal in its folder, then use the setup script for your system.

### macOS

```sh
chmod +x scripts/setup-macos.sh
./scripts/setup-macos.sh
```

### Windows (PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-windows.ps1
```

### Linux

```sh
chmod +x scripts/setup-linux.sh
./scripts/setup-linux.sh
```

The scripts create `.venv`, install the application, create the correct user folders, and copy the example configuration if needed. They never ask you to expose a key in terminal history.

You can also install manually:

```sh
python3 -m venv .venv
. .venv/bin/activate                 # Windows: .venv\Scripts\Activate.ps1
python -m pip install .
```

Then create the user configuration from [`config.example.json`](config.example.json)
using the location for your operating system shown below. The setup scripts do this
for you. For an editable development install, use `python -m pip install -e .`.

## Get a Rebrickable API key

1. Go to [Rebrickable](https://rebrickable.com/) and create an account or sign in.
2. Open the API section in your account settings.
3. Generate an API key.
4. Run `lego-lookup config-path` to find your configuration file.
5. Open that file in a text editor and replace `YOUR_API_KEY_HERE` with the key.
6. Do not share the key or commit the configuration file to Git.

The configuration must remain valid JSON, including the quotation marks around the
key and set number. Downloading is the only operation that requires the API key.

As an alternative, set `REBRICKABLE_API_KEY` in your environment. `LEGO_LOOKUP_SET` changes the default set. Environment variables override the config file.

## User file locations

| System | Configuration | Cache |
|---|---|---|
| macOS | `~/Library/Application Support/lego-element-lookup/config.json` | `~/Library/Caches/lego-element-lookup/` |
| Windows | `%APPDATA%\lego-element-lookup\config.json` | `%LOCALAPPDATA%\lego-element-lookup\cache\` |
| Linux | `~/.config/lego-element-lookup/config.json` | `~/.cache/lego-element-lookup/` |

`XDG_CONFIG_HOME` and `XDG_CACHE_HOME` are respected on Linux. Print the actual paths with `lego-lookup config-path` and `lego-lookup cache-path`.

## Command-line interface

Download the test set once:

```sh
lego-lookup download 76344-1
```

Refresh it later with `lego-lookup update 76344-1`. Both commands follow every Rebrickable results page and replace the cache only after a successful download.

Start the continuous prompt:

```sh
lego-lookup
```

The prompt stays open so you can paste parts one after another:

```text
LEGO Element Lookup
Paste an element ID, or type q to quit.

Element ID: 6212040

Part code:    35480
Colour code:  154

Part name:    Plate Special 1 x 2 Rounded with 2 Open Studs
Colour:       Dark red
Swatch:       ██████████  #720E0F
Inventory:    quantity 22

Part code copied to clipboard.

Element ID:
```

Enter one part at a time. Empty input is ignored; `q`, `quit`, `exit`, Ctrl+C, or Ctrl+D closes it cleanly. Invalid input or a missing element reports the problem and returns to the prompt. For a single lookup:

```sh
lego-lookup 6212040
lego-lookup 6293739
```

The original explicit form remains available for scripts and backwards compatibility:

```sh
lego-lookup lookup 6212040
```

The second bare-ID example can match the filename `6293739.jpg` even when the entry's top-level ID differs. Bare values must contain digits only; command names such as `download` and `config-path` remain unambiguous.

### Colour swatches

Lookup results always show the cached RGB hex code. On a compatible terminal, the block beside it uses ANSI true colour. Redirected output, terminals without colour support, invalid or missing RGB data, and the following opt-outs produce a plain fallback without ANSI escape sequences:

```sh
lego-lookup --no-colour 6212040
NO_COLOR=1 lego-lookup 6212040       # macOS and Linux
```

In PowerShell, use `$env:NO_COLOR=1` before running the command. The colour swatch uses cached data and does not cause a network request.

## Clipboard behaviour

macOS uses `pbcopy` and Windows uses `clip`. Linux tries `wl-copy`, then `xclip`, then `xsel`. Install one with your package manager—for example `sudo apt install wl-clipboard` on a Wayland desktop or `sudo apt install xclip` on X11. A missing or unavailable clipboard command produces a clear warning but never loses the lookup result or crashes the program.

## Troubleshooting

- **No cached inventory:** run `lego-lookup download SET-NUM`, including the suffix such as `76344-1`.
- **No API key configured:** edit the path printed by `lego-lookup config-path`, or set `REBRICKABLE_API_KEY`.
- **API key rejected:** check for extra spaces and generate a fresh key in Rebrickable account settings if necessary.
- **No match:** confirm the active set in the configuration and the digits from the instruction manual.
- **Clipboard unavailable on Linux:** install `wl-clipboard`, `xclip`, or `xsel`. The displayed code can still be copied manually.
- **Invalid cache JSON:** run `lego-lookup update SET-NUM` to safely replace it.

## Security and privacy

The application sends the API key only in Rebrickable's required `Authorization` header during download. It never prints the key. Normal lookups make no network request. Local `config.json` and `cache/*.json` files are ignored by Git; verify staged files before every commit. If a key has ever been exposed, revoke and replace it immediately.

LEGO is a trademark of the LEGO Group, which does not sponsor or endorse this project. Rebrickable data remains subject to Rebrickable's terms.

## Release history

See [CHANGELOG.md](CHANGELOG.md) for version history. Version 1.0.0 is the first
public release.

## Current limitations

- The app does not update itself. **Check for updates** opens GitHub Releases only.
- Desktop builds are unsigned beta builds; they are not notarised or signed with a Developer ID or Authenticode certificate.
- Relationship codes are direct catalogue relationships, not guarantees of functional interchangeability.
- MOC import, Mecabricks project integration, and native macOS glass/vibrancy are not included.

## Future roadmap

### Lite / Portable edition

A future lightweight edition could support older or low-resource systems with a CLI-first,
minimal-dependency build. It may be offered as `lego-lookup-lite.py`, a small Python package,
or a portable zip, with no desktop GUI, installer, or Pillow preview dependency required by
default. Its core scope would remain offline element-ID → part-code and colour-code lookup;
advanced desktop and preview features could stay separate.

This is future work and is not included in v1.4.0.

## Development

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e . pytest
pytest
```

Tests use small local fixtures and never contact Rebrickable. GitHub Actions tests Python 3.10–3.13 on Linux, macOS, and Windows.

To build release archives:

```sh
python -m pip install build
python -m build
```

The resulting wheel and source archive appear in `dist/` and can be attached to a GitHub Release.
