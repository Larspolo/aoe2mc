"""#4565 (epic #4561): a converted saved game starts each player with the resources, the age and the technologies of
the save (aoe2mc.json "players"), through the start values of the scenario path (scenario.start_values)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import build  # noqa: E402
import scenario  # noqa: E402
from test_saved_game import cut  # noqa: E402
from test_scenario_mode import game  # noqa: E402

import aoe2mc  # noqa: E402

STOCK = {"food": 1234, "wood": 567, "gold": 89, "stone": 10}


def test_aoe2mc_json_has_the_resources_and_the_age_of_each_player_of_the_save(tmp_path):
    aoe2mc.main([cut(tmp_path), str(tmp_path / "W")])
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        players = json.load(f)["players"]
    for n in ("1", "2"):
        p = players[n]
        assert p["saved"] and p["age"] in aoe2mc.SAVE_AGES
        assert set(p["resources"]) == set(aoe2mc.SAVE_RESOURCES) and all(v >= 0 for v in p["resources"].values())
    assert players["1"]["resources"] != players["2"]["resources"]   # the civilizations of the sample give other gold


def test_each_player_starts_with_the_stock_age_and_technologies_of_the_save():
    _, g, bot = game({"0": {}, "1": {"resources": STOCK, "age": "castle", "techs": ["HAND_CART"], "saved": True},
                      "2": {"resources": dict(STOCK, food=5), "age": "feudal", "saved": True}})
    for x in (g, bot):
        scenario.start_values(x, g.players[str(x.player)])
    assert build.ages(g) == 2 and build.ages(bot) == 1
    assert "HAND_CART" in g.techs and "HAND_CART" not in bot.techs   # a Castle Age technology: not from the age
    assert g.stock == STOCK and bot.stock == dict(STOCK, food=5)   # no research cost changes the stock
