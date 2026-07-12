"""Command-line interface."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Mapping, TextIO

from .clipboard import copy
from .config import ConfigError, cache_dir, config_path, load_settings
from .downloader import DownloadError, download_inventory
from .lookup import CacheError, Match, find_matches, load_inventory
from .secrets import SecretStore, resolve_api_key
from .services import ApplicationService


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="lego-lookup",
        usage="lego-lookup [--no-colour] [ELEMENT_ID | COMMAND] ...",
        description="Look up LEGO element IDs offline.",
        epilog="A bare numerical ELEMENT_ID is shorthand for: lego-lookup lookup ELEMENT_ID",
    )
    result.add_argument("--no-colour", action="store_true", help="disable ANSI colour output")
    commands = result.add_subparsers(dest="command")
    lookup = commands.add_parser("lookup", help="look up one element and exit")
    lookup.add_argument("element_id")
    for name in ("download", "update"):
        command = commands.add_parser(name, help=f"{name} a cached set inventory")
        command.add_argument("set_num", nargs="?")
    commands.add_parser("config-path", help="print the configuration path")
    commands.add_parser("cache-path", help="print the cache directory")
    return result


COMMANDS = {"lookup", "download", "update", "config-path", "cache-path"}
RGB_PATTERN = re.compile(r"#?([0-9a-fA-F]{6})\Z")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    values = list(sys.argv[1:] if argv is None else argv)
    no_colour = "--no-colour" in values
    values = [value for value in values if value != "--no-colour"]
    if values and values[0] not in COMMANDS and not values[0].startswith("-"):
        if not values[0].isdigit():
            parser().error(
                f"invalid bare element ID {values[0]!r}; enter digits only or use one of: "
                f"{', '.join(sorted(COMMANDS))}"
            )
        values.insert(0, "lookup")
    args = parser().parse_args(values)
    args.no_colour = no_colour
    return args


def format_swatch(
    rgb: str | None,
    *,
    no_colour: bool = False,
    stream: TextIO = sys.stdout,
    env: Mapping[str, str] | None = None,
) -> str:
    match = RGB_PATTERN.fullmatch(str(rgb or "").strip())
    if not match:
        return str(rgb).strip() if rgb else "Unknown"
    hex_code = f"#{match.group(1).upper()}"
    values = os.environ if env is None else env
    is_tty = bool(getattr(stream, "isatty", lambda: False)())
    ansi_enabled = not no_colour and "NO_COLOR" not in values and values.get("TERM") != "dumb" and is_tty
    if not ansi_enabled:
        return f"██████████  {hex_code}"
    red, green, blue = (int(hex_code[index : index + 2], 16) for index in (1, 3, 5))
    return f"\033[38;2;{red};{green};{blue}m██████████\033[0m  {hex_code}"


def print_match(match: Match, *, no_colour: bool = False) -> None:
    print(f"Part code:    {match.part_code}")
    print(f"Colour code:  {match.colour_code}")
    print()
    print(f"Part name:    {match.part_name}")
    print(f"Colour:       {match.colour_name}")
    print(f"Swatch:       {format_swatch(match.rgb, no_colour=no_colour, stream=sys.stdout)}")
    if match.quantity or match.spare_quantity:
        quantities = [f"quantity {match.quantity}"] if match.quantity else []
        if match.spare_quantity:
            quantities.append(f"spares {match.spare_quantity}")
        print(f"Inventory:    {', '.join(quantities)}")
    success, message = copy(match.part_code)
    print(f"\n{message}")


def lookup_once(element_id: str, set_num: str, directory: Path, *, no_colour: bool = False) -> bool:
    if not element_id.isdigit():
        print("Please enter a numerical LEGO element ID.", file=sys.stderr)
        return False
    matches = ApplicationService.lookup_cached(element_id, set_num, directory)
    if not matches:
        print(f"No match found for element ID {element_id} in set {set_num}.")
        return False
    for index, match in enumerate(matches):
        if index:
            print("\n---\n")
        print_match(match, no_colour=no_colour)
    return True


def interactive(set_num: str, directory: Path, *, no_colour: bool = False) -> int:
    path = directory / f"{set_num}.json"
    inventory = load_inventory(path)
    print("LEGO Element Lookup")
    print("Paste an element ID, or type q to quit.")
    while True:
        try:
            value = input("\nElement ID: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0
        if value.lower() in {"q", "quit", "exit"}:
            print("Goodbye.")
            return 0
        if not value:
            continue
        if not value.isdigit():
            print("Please enter a numerical LEGO element ID.")
            continue
        matches = find_matches(inventory, value)
        if not matches:
            print(f"No match found for element ID {value} in set {set_num}.")
        for index, match in enumerate(matches):
            if index:
                print("\n---")
            print()
            print_match(match, no_colour=no_colour)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "config-path":
        print(config_path())
        return 0
    if args.command == "cache-path":
        print(cache_dir())
        return 0
    try:
        settings = load_settings()
        directory = getattr(settings, "cache_directory", None) or cache_dir()
        set_num = getattr(args, "set_num", None) or settings.default_set
        if args.command in {"download", "update"}:
            api_key = resolve_api_key(SecretStore(), settings.api_key)
            if not api_key:
                print(f"No Rebrickable API key is configured. Add it to {config_path()} or set REBRICKABLE_API_KEY.", file=sys.stderr)
                return 2
            count = download_inventory(set_num, api_key, directory / f"{set_num}.json")
            print(f"Downloaded {count} inventory entries for set {set_num} to {directory / f'{set_num}.json'}")
            return 0
        if args.command == "lookup":
            return 0 if lookup_once(args.element_id, settings.default_set, directory, no_colour=args.no_colour) else 1
        return interactive(settings.default_set, directory, no_colour=args.no_colour)
    except (ConfigError, CacheError, DownloadError) as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
