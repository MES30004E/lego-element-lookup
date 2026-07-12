# LEGO Element Lookup

[![Tests](https://github.com/MES30004E/lego-element-lookup/actions/workflows/tests.yml/badge.svg)](https://github.com/MES30004E/lego-element-lookup/actions/workflows/tests.yml)

LEGO Element Lookup is a small command-line tool for people rebuilding LEGO sets in Mecabricks. Enter the element ID printed in an instruction manual and it reports the part code first, the official LEGO colour code second, plus their names. The part code is copied to the clipboard automatically.

Lookups use a downloaded Rebrickable set inventory and are fully offline. The tool checks both Rebrickable's top-level `element_id` and the element number in `part_img_url`, because either can contain the manual's identifier.

```text
$ lego-lookup lookup 6212040
Part code:    35480
Colour code:  154

Part name:    Plate Special 1 x 2 Rounded with 2 Open Studs
Colour:       Dark red

Part code copied to clipboard.
```

## Requirements

- Python 3.10 or newer
- A free Rebrickable account and API key for downloading inventories
- Internet access only while downloading or updating a set
- On Linux, `wl-copy`, `xclip`, or `xsel` for automatic clipboard copying

There are no third-party runtime Python dependencies.

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

## Use the tool

Download the test set once:

```sh
lego-lookup download 76344-1
```

Refresh it later with `lego-lookup update 76344-1`. Both commands follow every Rebrickable results page and replace the cache only after a successful download.

Start the continuous prompt:

```sh
lego-lookup
```

Enter one part at a time. Empty input is ignored; `q`, `quit`, or `exit` closes it. For a single lookup:

```sh
lego-lookup lookup 6212040
lego-lookup lookup 6293739
```

The second example can match the filename `6293739.jpg` even when the entry's top-level ID differs.

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
