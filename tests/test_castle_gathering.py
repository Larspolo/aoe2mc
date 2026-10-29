"""game/train.py and game/gather.py: the lumber camp researches Bow Saw (villagers chop wood faster) and the mining
camp Gold Shaft Mining and Stone Shaft Mining (gold or stone faster) in the Castle Age, each after its Feudal Age
technology (#1423)."""
from urllib.parse import unquote

import pytest
from test_castle_upgrades import entry
from test_gather import FakeServer, grid

from game import gather, train

LINES = [("BOW_SAW", "LUMBER_CAMP", "wood"), ("GOLD_SHAFT_MINING", "MINING_CAMP", "gold"),
         ("STONE_SHAFT_MINING", "MINING_CAMP", "stone")]


def setup(camp, *techs):
    """A flat 16 × 16 map (tile size 1): a camp of player 1 at blocks x 2-3, z 2-3 and a villager, in the Castle Age."""
    objects = [{"kind": "building", "name": camp, "player": 1, "tile": [3.0, 3.0], "footprint": [2, 2, 4, 4]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.stock.update(food=500, wood=500)
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE", *techs}
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


@pytest.mark.parametrize("tech, camp, res", LINES)
def test_the_menu_shows_the_castle_technology_after_its_feudal_technology(tech, camp, res):
    before, label = train.BY_KEY["after"][tech], train.ITEMS[tech][2]
    server, g = setup(camp)
    train.open_menu(g, "Steve", (3, 3))
    assert f":book:{label}:" not in menus(server)[-1] and train.queue(g, "Steve", (3, 3), tech) is None
    server, g = setup(camp, before)
    train.open_menu(g, "Steve", (3, 3))
    assert " " + entry(g, (3, 3), tech) + "research " in menus(server)[-1] + " "
    server, g = setup(camp, before)                                # the Feudal Age: not yet
    g.techs.discard("CASTLE_AGE")
    assert train.queue(g, "Steve", (3, 3), tech) is None


@pytest.mark.parametrize("tech, camp, res", LINES)
def test_after_the_research_the_villagers_gather_faster(tech, camp, res):
    server, g = setup(camp, train.BY_KEY["after"][tech])
    old = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, train.ITEMS[tech][0]) == 1
    assert (g.stock["food"], g.stock["wood"]) == (500 - train.COSTS[tech].get("food", 0), 500 - train.COSTS[tech].get("wood", 0))
    train.tick(g, train.TRAIN_TIMES[tech])
    assert tech in g.techs
    assert g.work_time(res) < old[res]
    assert {r: g.work_time(r) for r in old if r != res} == {r: t for r, t in old.items() if r != res}
    train.open_menu(g, "Steve", (3, 3))
    assert train.ITEMS[tech][2] not in menus(server)[-1]
