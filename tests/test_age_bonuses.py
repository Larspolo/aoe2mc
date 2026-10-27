"""game/train.py: the age-up bonuses of the civilizations (#1926, game/civs.py AGE_*): Dravidians get 200 wood and
Ethiopians 100 food and 100 gold at each new age, the Muisca pay half the gold for an age, the Malay advance 66 % faster,
each Bengali town center spawns 2 villagers, and the Khmer need no buildings to advance."""
import contextlib
import io
import json

import pytest
from test_feudal_age import add
from test_loom import setup

from game import gather, run, train


def game(civ, **stock):
    server, g = setup(**stock)
    g.data["players"] = {"1": {"civ": civ}}
    return server, g


def advance(g, name="FEUDAL_AGE"):
    """Order the age at the town center and research it to the end."""
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, train.ITEMS[name][0]) == 1
    train.tick(g, 1000)
    assert name in g.techs
    return rect


def test_dravidians_get_200_wood_and_ethiopians_100_food_and_100_gold_at_each_age():
    for civ, gift in (("DRAVIDIANS", {"wood": 200}), ("ETHIOPIANS", {"food": 100, "gold": 100}), ("BRITONS", {})):
        server, g = game(civ, food=500, gold=0)
        add(g, "BARRACKS", "MILL")
        after = {r: v - 500 * (r == "food") + gift.get(r, 0) for r, v in g.stock.items()}   # the age costs 500 food
        advance(g)
        assert g.stock == after, civ
        assert all(f"scoreboard players add {r.capitalize()} aoe_res {v}" in server.log for r, v in gift.items())


def test_the_muisca_pay_half_the_gold_for_an_age():
    for civ, gold in (("MUISCA", 400), ("BRITONS", 800)):
        server, g = game(civ)
        g.techs.update({"FEUDAL_AGE", "CASTLE_AGE"})
        assert train.price(g, "IMPERIAL_AGE") == {"food": 1000, "gold": gold}, civ
    server, g = game("MUISCA")
    assert train.price(g, "LOOM") == {"gold": 50}                       # not other technologies


def test_the_malay_advance_66_percent_faster():
    server, g = game("MALAY")
    assert train.seconds(g, "FEUDAL_AGE", "TOWN_CENTER") == 130 / 1.66
    assert train.seconds(g, "LOOM", "TOWN_CENTER") == 25 and train.seconds(g, "VILLAGER_MALE", "TOWN_CENTER") == 25
    server, g = game("BRITONS")
    assert train.seconds(g, "FEUDAL_AGE", "TOWN_CENTER") == 130


def test_each_bengali_town_center_spawns_2_villagers_at_an_age():
    for civ, new in (("BENGALIS", 2), ("BRITONS", 0)):
        server, g = game(civ, food=500)
        add(g, "BARRACKS", "MILL")
        villagers, pop = len(g.villagers), g.pop
        advance(g)
        assert len(g.villagers) - villagers == new and g.pop - pop == new, civ
        assert sum(c.startswith("summon minecraft:villager") for c in server.log) == new, civ


def test_the_khmer_need_no_buildings_to_advance():
    server, g = game("KHMER", food=500)
    assert train.missing(g, "FEUDAL_AGE") is None
    advance(g)
    server, g = game("BRITONS", food=500)
    assert train.missing(g, "FEUDAL_AGE").startswith("needs 2 of")


@pytest.mark.mc
def test_a_bengali_town_center_spawns_2_villagers_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not mojang_reachable() or not paper_reachable():
        pytest.skip("Mojang or Paper is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=5.5, y=5.5)
    src = str(tmp_path / "tc.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    data["players"]["1"]["civ"] = "BENGALIS"
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        before = set(g.villagers)
        train.research(g, {"name": "FEUDAL_AGE", "player": "nobody"})   # the end of the age research
        new = set(g.villagers) - before
        assert "FEUDAL_AGE" in g.techs and len(new) == 2
        assert len(g.positions(list(new))) == 2                         # two live villagers on the server
