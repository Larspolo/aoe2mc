"""#3296 (epic #2538): each player of a scenario game starts in the starting age of the scenario (tab "Players" of
the editor, aoe2mc.json "players" "age"), and a player in the Dark Age has no "age" key."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import build  # noqa: E402
import scenario  # noqa: E402
import scenarios  # noqa: E402
from AoE2ScenarioParser.datasets.object_support import StartingAge  # noqa: E402
from test_scenario_mode import START, game  # noqa: E402

import aoe2mc  # noqa: E402


def test_aoe2mc_json_has_the_starting_age_of_each_player(tmp_path):
    scn = scenarios.new_scenario(24)
    scn.player_manager.players[1].starting_age = StartingAge.CASTLE_AGE
    src = scenarios.save(scn, str(tmp_path / "s.aoe2scenario"))
    aoe2mc.main([src, str(tmp_path / "W")])
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        players = json.load(f)["players"]
    assert players["1"]["age"] == "castle"
    assert "age" not in players["2"]


def test_each_player_starts_in_its_scenario_age():
    _, g, bot = game({"0": {}, "1": {"resources": START, "age": "castle"},
                      "2": {"resources": START, "age": "feudal"}})
    scenario.setup(g, "scenario")
    assert build.ages(g) == 2 and build.ages(bot) == 1
    assert g.stock == START and bot.stock == START        # no age cost changes the start resources


def test_a_player_without_an_age_stays_in_the_dark_age():
    _, g, bot = game({"0": {}, "1": {"resources": START}, "2": {"resources": START}})
    scenario.setup(g, "scenario")
    assert build.ages(g) == 0 and build.ages(bot) == 0
