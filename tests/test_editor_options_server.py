"""The Options and Map tabs of the editor on a real server (#6087, epic #6075): one disabled technology, building and
unit of player 1 and a color mood of the menu go into the saved scenario, and aoe2mc.convert reads them back."""
import contextlib
import io
import json
import os
import sys

import pytest
from test_mc_check import mojang_reachable

import aoe2mc
from tools import scenarios

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))


@pytest.mark.mc
def test_editor_options_and_mood_save_and_convert(tmp_path):
    from test_paper import paper_reachable
    if not mojang_reachable() or not paper_reachable():
        pytest.skip("Mojang or Paper is not available")
    import editor
    from AoE2ScenarioParser.datasets.trigger_lists import ColorMood

    from game import run
    world, out = str(tmp_path / "W"), str(tmp_path / "OUT.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(scenarios.tiny(str(tmp_path / "tiny.aoe2scenario")), world)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    source = data.get("mood", "DEFAULT")
    with run.Game(world) as game:
        s = editor.State(game, data)
        s.player, s.menus = 1, {}
        off = set(s.data["players"]["1"].get("disabled", ()))
        want = set()
        for tab in range(len(editor.OPTION_TABS)):                     # the first name of each tab that is on
            editor.options_menu(s, "p", tab)
            names = editor.option_names(tab)[:editor.PAGE]
            slot = next(i for i, n in enumerate(names) if n not in off)
            s.menus["p"]("p", slot, False)
            want.add(names[slot])
        s.menus["p"]("p", editor.MOOD_SLOT, False)
        while s.data["mood"] == source or s.data["mood"] not in ColorMood.__members__:
            s.menus["p"]("p", editor.MOOD_SLOT, False)
        mood = s.data["mood"]
        with contextlib.redirect_stdout(io.StringIO()):
            editor.save(game, out, s)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(out, str(tmp_path / "W2"))
    with open(os.path.join(tmp_path, "W2", "aoe2mc.json")) as f:
        back = json.load(f)
    assert want <= set(back["players"]["1"].get("disabled", ())), (want, back["players"]["1"].get("disabled"))
    assert back["mood"] == mood != source                              # the editor wins over the source
