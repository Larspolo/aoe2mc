"""gui.py, tab "Play": the attack time of the bot (--bot-attack) goes to game/run.py only with --bot (#1870)."""
from pathlib import Path

import pytest

import gui

ROOT = Path(__file__).resolve().parent.parent


def test_bot_attack_only_with_the_bot():
    o = {"world": "W", "bot_attack": " 5:00 "}
    assert gui.play_argv(o | {"bot": True})[1:] == ["--bot-attack", "5:00", "--bot"]
    assert gui.play_argv(o) == ["W"]
    assert gui.play_argv(o | {"bot": True, "bot_attack": ""})[1:] == ["--bot"]
    assert "--bot-attack" not in gui.play_argv(o | {"bot": True, "replay": True})


def test_bot_attack_is_valid_for_run_py(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "game"))
    import run
    with pytest.raises(SystemExit, match="no level.dat in W"):  # argparse accepts the option, then the world check
        run.main(gui.play_argv({"world": "W", "bot": True, "bot_attack": "5:00", "play": True}))
