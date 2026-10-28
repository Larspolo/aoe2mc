"""gui.game_problem (#3051): a pip or pipx install has no game/run.py, so the window says so before it starts a game."""
import os
import sys

import gui


def test_a_missing_game_program_gives_the_installer_and_the_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(gui, "GAME", tmp_path / "game" / "run.py")
    text = gui.game_problem()
    assert "no game program" in text and "pip and pipx" in text
    assert "the release" in text and "python3 game/run.py WORLD" in text


def test_a_checkout_has_the_game_program():
    assert gui.game_problem() is None                                  # game/run.py of this checkout


def test_an_app_bundle_looks_for_aoe2mc_game_next_to_the_window(monkeypatch, tmp_path):
    name = "aoe2mc-game" + ".exe" * (os.name == "nt")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / ("aoe2mc-gui" + ".exe" * (os.name == "nt"))))
    assert "aoe2mc-game" in gui.game_problem() and "Install the release again" in gui.game_problem()
    (tmp_path / name).touch()
    assert gui.game_problem() is None
