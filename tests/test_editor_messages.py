"""The editor sets the team, the victory and the messages (#6032): they go into the scenario."""
import contextlib
import io
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
from AoE2ScenarioParser.datasets.trigger_lists import VictoryCondition  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402
from test_editor_palette import state_of  # noqa: E402


def test_team_and_victory_items_cycle(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    s.data["players"]["1"].pop("team", None)
    editor.players_menu(s, "p")
    s.menus["p"]("p", 1, False)
    teams = []
    for _ in range(editor.TEAMS + 1):
        s.menus["p"]("p", editor.TEAM, False)
        teams.append(s.data["players"]["1"].get("team"))
    assert teams == [*range(1, editor.TEAMS + 1), None]
    seen = set()
    for _ in editor.victories():
        s.menus["p"]("p", editor.WIN, False)
        seen.add(s.data["victory"]["condition"])
    assert seen == set(editor.victories())
    while s.data["victory"]["condition"] != "conquest":
        s.menus["p"]("p", editor.WIN, False)
    s.menus["p"]("p", 2, False)
    s.menus["p"]("p", editor.TEAM, False)
    s.menus["p"]("p", 1, False)
    s.menus["p"]("p", editor.TEAM, False)                             # players 1 and 2: team 1
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(s.game, out, s)
        scn = AoE2DEScenario.from_file(out)
    assert scn.option_manager.victory_condition == VictoryCondition.CONQUEST.value
    import aoe2mc
    teams = aoe2mc.scenario_teams(scn.player_manager.players)
    assert teams.get(1) is not None and teams.get(1) == teams.get(2)


def test_books_round_trip(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    s.data["messages"] = {"hints": "x" * 1100, "loss": "x" * 5000}
    editor.books(s, "p")
    gives = [c for c in s.game.sent if c.startswith("give p minecraft:writable_book")]
    assert len(gives) == len(editor.chapters()) - 1                 # the long loss text: no book
    assert any('aoe_msg:"hints"' in c and c.count("{raw:") == 2 for c in gives)
    answer = 'p has the following entity data: [{raw: "Mine \\"gold\\"."}, {raw: \'first\'}]'
    s.game.command = lambda c: answer if 'aoe_msg:"hints"' in c else "Found no elements matching"
    editor.read_books(s)
    assert s.data["messages"]["hints"] == 'Mine "gold".first'
