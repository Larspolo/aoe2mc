"""The players menu of the editor (#6003): the civilization, resources and age go into the scenario, and the current
player owns the next object of the palette."""
import contextlib
import io
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import civs  # noqa: E402
import editor  # noqa: E402
import export  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402
from test_editor_palette import eye_over, free_cells, state_of  # noqa: E402


def test_players_menu_values_go_into_the_scenario(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    editor.players_menu(s, "p")
    s.menus["p"]("p", 2, False)                                       # player 2
    assert s.player == 2
    old = s.data["players"].get("2", {}).get("civ")
    s.menus["p"]("p", editor.CIV, False)
    civ = s.data["players"]["2"]["civ"]
    assert civ != old and civ in [r["name"] for r in civs.ROWS]
    for _ in range(3):
        s.menus["p"]("p", editor.RES, False)                          # food +300
    s.menus["p"]("p", editor.RES + 2, False)
    s.menus["p"]("p", editor.RES + 2, True)                           # gold +100 -100
    s.menus["p"]("p", editor.AGE + 2, False)                          # the third age
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(s.game, out, s)
        scn = AoE2DEScenario.from_file(out)
    pl = scn.player_manager.players[2]
    assert pl.civilization.name == civ or civ not in export.Civilization.__members__
    assert pl.food == 300 and pl.gold == 0
    assert pl.starting_age == export.AGES[2]


def test_the_current_player_owns_the_next_object(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    editor.players_menu(s, "p")
    s.menus["p"]("p", 3, False)
    house = dict(editor.tabs())["buildings"][0]
    assert editor.place(s, "p", house, *eye_over(s, free_cells(s, 1)[0]))["player"] == 3
