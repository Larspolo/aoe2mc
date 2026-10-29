"""#2521: each game mode of `run.py --play --mode` is one line in game/data/setup.jsonl and one module with a setup():
play() reads the line, not an own list of the modes."""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import defend_wonder  # noqa: E402
import empire_wars  # noqa: E402
import run  # noqa: E402
import table  # noqa: E402
import train  # noqa: E402
from test_mode_on_top import play  # noqa: E402


def test_the_modes_come_from_the_data_lines():
    lines = {r["name"]: r for r in table.load("setup.jsonl") if "help" in r}
    assert run.MODES == lines and "standard" in lines                 # the default of --mode
    for line in lines.values():
        if "module" in line:
            assert callable(importlib.import_module(line["module"]).setup), line["name"]


def test_the_mode_help_comes_from_the_data_lines(capsys):
    try:
        run.main(["--help"])
    except SystemExit:
        pass
    text = "".join(capsys.readouterr().out.split())                   # argparse wraps the lines
    for name, line in run.MODES.items():
        if name != "standard":
            assert "".join(f"{name}: {line['help']}".split()) in text, name


def test_defend_the_wonder_gets_start_false_in_a_loaded_game(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(defend_wonder, "setup", lambda g, mode, start=True: calls.append((mode, start)))
    play(tmp_path, monkeypatch, mode="defend-the-wonder")
    play(tmp_path, monkeypatch, mode="defend-the-wonder", state={"players": {}})
    assert calls == [("defend-the-wonder", True), ("defend-the-wonder", False)]


def test_two_modes_with_a_start_age_start_in_the_later_age(tmp_path, monkeypatch):
    monkeypatch.setattr(defend_wonder, "setup", lambda g, mode, start=True: None)
    monkeypatch.setattr(empire_wars, "setup", lambda g, mode: None)
    seen = play(tmp_path, monkeypatch, mode="defend-the-wonder", empire_wars=True)
    ages = [run.MODES[m]["age"] for m in ("defend-the-wonder", "empire-wars")]
    assert seen[0] == f"age {max(ages, key=lambda a: train.STARTS[a]['ages'])}"
