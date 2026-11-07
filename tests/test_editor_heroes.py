"""The heroes and the other units in the palette of the editor (#6035)."""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
import export  # noqa: E402
import train  # noqa: E402
from AoE2ScenarioParser.datasets.heroes import HeroInfo  # noqa: E402
from test_editor_palette import eye_over, free_cells, state_of  # noqa: E402

import units  # noqa: E402


def test_the_heroes_tab_and_the_other_units():
    tabs = dict(editor.tabs())
    assert set(tabs["heroes"]) == {e.name for e in HeroInfo if units.classify(e.name, True)} != set()
    trained = {r["name"] for r in train.UNIT_ROWS}
    assert any(n not in trained for n in tabs["units"])
    assert all(export.unit_id(n) is not None for n in tabs["units"] + tabs["heroes"])


def test_place_puts_a_hero_of_the_current_player(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    s.player = 2
    hero = dict(editor.tabs())["heroes"][0]
    o = editor.place(s, "p", hero, *eye_over(s, free_cells(s, 1)[0]))
    assert o is not None and o["player"] == 2 and o["id"] == export.unit_id(hero) and o.get("unit")
    assert any(c.startswith("summon ") and "aoe2mc.p2" in c for c in s.game.sent)
