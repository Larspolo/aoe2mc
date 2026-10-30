"""#3299 (epic #2538): the technologies, buildings and units that a scenario disables for a player (tab "Options" of
the editor) go into aoe2mc.json "players" "disabled", and the scenario mode keeps them out of the menus."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import civs  # noqa: E402
import scenario  # noqa: E402
import scenarios  # noqa: E402
from test_scenario_mode import START, game  # noqa: E402

import aoe2mc  # noqa: E402

OFF = ["CASTLE", "KNIGHT", "LOOM"]


def test_aoe2mc_json_lists_the_disabled_items_of_each_player(tmp_path):
    scn = scenarios.new_scenario(24)
    one = scn.player_manager.players[1]
    one.disabled_buildings, one.disabled_units, one.disabled_techs = [82], [38], [22]   # Castle, Knight, Loom
    src = scenarios.save(scn, str(tmp_path / "s.aoe2scenario"))
    aoe2mc.main([src, str(tmp_path / "W")])
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        players = json.load(f)["players"]
    assert players["1"]["disabled"] == OFF
    assert "disabled" not in players["2"]


def test_the_disabled_items_are_not_in_the_menus_until_a_trigger_enables_them():
    server, g, bot = game({"0": {}, "1": {"resources": START, "disabled": OFF}, "2": {"resources": START}})
    scenario.setup(g, "scenario")
    assert all(civs.missing(g, n) for n in OFF)
    assert not any(civs.missing(bot, n) for n in OFF)
    g.trigger_menus["KNIGHT"] = True                     # what scenario.menus does for "Enable Object"
    assert not civs.missing(g, "KNIGHT") and civs.missing(g, "CASTLE")
