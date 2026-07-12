"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .clipboard import copy
from .config import ConfigError, cache_dir, config_path, load_settings
from .downloader import DownloadError, download_inventory
from .lookup import CacheError, Match, find_matches, load_inventory


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="lego-lookup", description="Look up LEGO element IDs offline.")
    commands = result.add_subparsers(dest="command")
    lookup = commands.add_parser("lookup", help="look up one element and exit")
    lookup.add_argument("element_id")
    for name in ("download", "update"):
        command = commands.add_parser(name, help=f"{name} a cached set inventory")
        command.add_argument("set_num", nargs="?")
    commands.add_parser("config-path", help="print the configuration path")
    commands.add_parser("cache-path", help="print the cache directory")
    return result


def print_match(match: Match) -> None:
    print(f"Part code:    {match.part_code}")
    print(f"Colour code:  {match.colour_code}")
    print()
    print(f"Part name:    {match.part_name}")
    print(f"Colour:       {match.colour_name}")
    if match.quantity or match.spare_quantity:
        quantities = [f"quantity {match.quantity}"] if match.quantity else []
        if match.spare_quantity:
            quantities.append(f"spares {match.spare_quantity}")
        print(f"Inventory:    {', '.join(quantities)}")
    success, message = copy(match.part_code)
    print(f"\n{message}")


def lookup_once(element_id: str, set_num: str, directory: Path) -> bool:
    if not element_id.isdigit():
        print("Please enter a numerical LEGO element ID.", file=sys.stderr)
        return False
    inventory = load_inventory(directory / f"{set_num}.json")
    matches = find_matches(inventory, element_id)
    if not matches:
        print(f"No match found for element ID {element_id} in set {set_num}.")
        return False
    for index, match in enumerate(matches):
        if index:
            print("\n---\n")
        print_match(match)
    return True


def interactive(set_num: str, directory: Path) -> int:
    path = directory / f"{set_num}.json"
    inventory = load_inventory(path)
    print(f"LEGO Element Lookup — set {set_num}")
    print(f"Loaded {len(inventory)} cached inventory entries.")
    print("Enter an element ID, or q to quit.")
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
            print_match(match)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "config-path":
        print(config_path())
        return 0
    if args.command == "cache-path":
        print(cache_dir())
        return 0
    try:
        settings = load_settings()
        directory = cache_dir()
        set_num = getattr(args, "set_num", None) or settings.default_set
        if args.command in {"download", "update"}:
            if not settings.api_key:
                print(f"No Rebrickable API key is configured. Add it to {config_path()} or set REBRICKABLE_API_KEY.", file=sys.stderr)
                return 2
            count = download_inventory(set_num, settings.api_key, directory / f"{set_num}.json")
            print(f"Downloaded {count} inventory entries for set {set_num} to {directory / f'{set_num}.json'}")
            return 0
        if args.command == "lookup":
            return 0 if lookup_once(args.element_id, settings.default_set, directory) else 1
        return interactive(settings.default_set, directory)
    except (ConfigError, CacheError, DownloadError) as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
