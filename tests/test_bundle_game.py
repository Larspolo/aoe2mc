"""The game program in the app bundles (#1778): in a frozen app the window starts aoe2mc-game next to itself, and the
game program uses the plugin jar of the bundle (no JDK, no Gradle)."""
import os
import sys

import gui
from game import run


def test_the_window_starts_the_game_program_next_to_itself_in_a_bundle(monkeypatch, tmp_path):
    assert gui.game_command()[1:] == ("-u", str(gui.GAME))             # a source checkout: game/run.py
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / ("aoe2mc-gui" + ".exe" * (os.name == "nt"))))
    assert gui.game_command() == (str(tmp_path / ("aoe2mc-game" + ".exe" * (os.name == "nt"))),)


def test_a_bundle_uses_its_plugin_jar(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(run, "build_plugin", lambda *a: (_ for _ in ()).throw(AssertionError("no Gradle in a bundle")))
    assert run.plugin_jar("26.3") == os.path.join(run.HERE, "plugin", "aoe2mc-plugin.jar")


def test_a_bundle_runs_its_servers_in_the_user_cache(monkeypatch, tmp_path):
    import mc_check
    monkeypatch.setattr(mc_check, "CACHE", str(tmp_path / "aoe2mc" / "mc"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)             # the folder of the app can be read-only
    assert mc_check.workdir() == str(tmp_path / "aoe2mc" / "servers") and os.path.isdir(mc_check.workdir())
