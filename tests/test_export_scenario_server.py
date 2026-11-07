"""The editor on a real server (#6032): the server takes the books of the messages, and a message, a team and the
victory of the editor go into the saved scenario. The server has no player, so the text of the book comes from
"messages" (read_books keeps a chapter with no book)."""
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
def test_editor_message_team_and_victory_are_saved(tmp_path):
    from test_paper import paper_reachable
    if not mojang_reachable() or not paper_reachable():
        pytest.skip("Mojang or Paper is not available")
    import editor
    from AoE2ScenarioParser.datasets.trigger_lists import VictoryCondition
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

    from game import run
    world, out = str(tmp_path / "W"), str(tmp_path / "OUT.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(scenarios.tiny(str(tmp_path / "tiny.aoe2scenario")), world)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    with run.Game(world) as game:
        s = editor.State(game, data)
        s.data["messages"] = {"hints": "Mine the gold first."}
        sent = []
        s.command = lambda c: sent.append(game.command(c)) or sent[-1]   # noqa: E731
        editor.books(s, "@a")
        assert sent and all("No player was found" in r for r in sent), sent   # the item parses
        editor.players_menu(s, "p")
        s.menus = {}
        for p in (1, 2):
            s.data["players"][str(p)]["team"] = None
            s.player = p
            editor.players_menu(s, "p")
            s.menus["p"]("p", editor.TEAM, False)
        while (s.data.get("victory") or {}).get("condition") != "conquest":
            s.menus["p"]("p", editor.WIN, False)
        with contextlib.redirect_stdout(io.StringIO()):
            editor.save(game, out, s)
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(out)
    assert scn.message_manager.hints == "Mine the gold first."
    assert scn.option_manager.victory_condition == VictoryCondition.CONQUEST.value
    teams = aoe2mc.scenario_teams(scn.player_manager.players)
    assert teams.get(1) is not None and teams.get(1) == teams.get(2)
