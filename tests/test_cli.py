from __future__ import annotations

import io
from pathlib import Path

import pytest

from lego_element_lookup import cli


class TTY(io.StringIO):
    def isatty(self) -> bool:
        return True


def session_input(values):
    iterator = iter(values)

    def fake_input(prompt):
        print(prompt, end="")
        value = next(iterator)
        if isinstance(value, BaseException):
            raise value
        print(value)
        return value

    return fake_input


def test_bare_element_id_parses_as_lookup():
    args = cli.parse_args(["6212040"])
    assert (args.command, args.element_id) == ("lookup", "6212040")


def test_explicit_lookup_remains_supported():
    args = cli.parse_args(["lookup", "6212040"])
    assert (args.command, args.element_id) == ("lookup", "6212040")


def test_no_arguments_enters_interactive_mode(monkeypatch):
    monkeypatch.setattr(cli, "load_settings", lambda: type("Settings", (), {"default_set": "76344-1"})())
    monkeypatch.setattr(cli, "cache_dir", lambda: None)
    called = {}

    def fake_interactive(set_num, directory, no_colour=False):
        called["set"] = set_num
        return 0

    monkeypatch.setattr(cli, "interactive", fake_interactive)
    assert cli.main([]) == 0
    assert called == {"set": "76344-1"}


@pytest.mark.parametrize("arguments", [["6212040"], ["lookup", "6212040"]])
def test_one_off_lookup_syntaxes_dispatch_identically(monkeypatch, arguments):
    monkeypatch.setattr(cli, "load_settings", lambda: type("Settings", (), {"default_set": "76344-1"})())
    monkeypatch.setattr(cli, "cache_dir", lambda: None)
    calls = []
    monkeypatch.setattr(
        cli,
        "lookup_once",
        lambda element_id, set_num, directory, no_colour=False: calls.append((element_id, set_num)) or True,
    )
    assert cli.main(arguments) == 0
    assert calls == [("6212040", "76344-1")]


@pytest.mark.parametrize("command", ["download", "update", "config-path", "cache-path"])
def test_existing_commands_still_parse(command):
    assert cli.parse_args([command]).command == command


def test_invalid_bare_value_has_clear_error(capsys):
    with pytest.raises(SystemExit):
        cli.parse_args(["not-an-element"])
    assert "invalid bare element ID" in capsys.readouterr().err


def test_valid_rgb_uses_true_colour_on_tty():
    swatch = cli.format_swatch("720e0f", stream=TTY(), env={})
    assert swatch == "\033[38;2;114;14;15m██████████\033[0m  #720E0F"


@pytest.mark.parametrize(("rgb", "expected"), [(None, "Unknown"), ("not-rgb", "not-rgb")])
def test_invalid_or_missing_rgb_fallback(rgb, expected):
    assert cli.format_swatch(rgb, stream=TTY(), env={}) == expected


def test_no_color_environment_disables_ansi():
    assert cli.format_swatch("720E0F", stream=TTY(), env={"NO_COLOR": ""}) == "██████████  #720E0F"


def test_no_colour_option_disables_ansi():
    args = cli.parse_args(["--no-colour", "6212040"])
    assert args.no_colour is True
    assert cli.format_swatch("720E0F", no_colour=args.no_colour, stream=TTY(), env={}) == "██████████  #720E0F"


def test_non_tty_output_disables_ansi():
    assert cli.format_swatch("720E0F", stream=io.StringIO(), env={}) == "██████████  #720E0F"


def test_interactive_repeats_lookups_and_copies_each_part(monkeypatch, capsys, entries):
    monkeypatch.setattr(cli, "load_inventory", lambda path: entries)
    monkeypatch.setattr("builtins.input", session_input(["  6212040  ", "6293739", "q"]))
    copied = []
    monkeypatch.setattr(cli, "copy", lambda part_code: (copied.append(part_code) or True, "Part code copied to clipboard."))

    assert cli.interactive("76344-1", Path(".")) == 0
    output = capsys.readouterr().out
    assert output.startswith("LEGO Element Lookup\nPaste an element ID, or type q to quit.\n\nElement ID:")
    assert output.count("Element ID:") == 3
    assert "Part code:    35480" in output
    assert "Part code:    2420" in output
    assert copied == ["35480", "2420"]
    assert output.endswith("Goodbye.\n")


@pytest.mark.parametrize("quit_value", ["q", "quit", "exit"])
def test_interactive_quit_values(monkeypatch, capsys, quit_value):
    monkeypatch.setattr(cli, "load_inventory", lambda path: [])
    monkeypatch.setattr("builtins.input", session_input([quit_value]))
    assert cli.interactive("76344-1", Path(".")) == 0
    assert capsys.readouterr().out.endswith("Goodbye.\n")


@pytest.mark.parametrize("interruption", [EOFError(), KeyboardInterrupt()])
def test_interactive_eof_and_ctrl_c(monkeypatch, capsys, interruption):
    monkeypatch.setattr(cli, "load_inventory", lambda path: [])
    monkeypatch.setattr("builtins.input", session_input([interruption]))
    assert cli.interactive("76344-1", Path(".")) == 0
    assert capsys.readouterr().out.endswith("\nGoodbye.\n")


def test_interactive_blank_and_non_numeric_input_return_to_prompt(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_inventory", lambda path: [])
    monkeypatch.setattr("builtins.input", session_input(["   ", "not-a-number", "q"]))
    assert cli.interactive("76344-1", Path(".")) == 0
    output = capsys.readouterr().out
    assert output.count("Element ID:") == 3
    assert "Please enter a numerical LEGO element ID." in output


def test_failed_lookup_can_be_followed_by_valid_lookup(monkeypatch, capsys, entries):
    monkeypatch.setattr(cli, "load_inventory", lambda path: entries)
    monkeypatch.setattr("builtins.input", session_input(["9999999", "6212040", "q"]))
    copied = []
    monkeypatch.setattr(cli, "copy", lambda part_code: (copied.append(part_code) or True, "Part code copied to clipboard."))
    assert cli.interactive("76344-1", Path(".")) == 0
    output = capsys.readouterr().out
    assert "No match found for element ID 9999999 in set 76344-1." in output
    assert "Part code:    35480" in output
    assert copied == ["35480"]


@pytest.mark.parametrize("no_colour", [False, True])
def test_interactive_propagates_colour_preference(monkeypatch, entries, no_colour):
    monkeypatch.setattr(cli, "load_inventory", lambda path: entries[:1])
    monkeypatch.setattr("builtins.input", session_input(["6212040", "q"]))
    preferences = []
    monkeypatch.setattr(cli, "print_match", lambda match, no_colour=False: preferences.append(no_colour))
    assert cli.interactive("76344-1", Path("."), no_colour=no_colour) == 0
    assert preferences == [no_colour]
