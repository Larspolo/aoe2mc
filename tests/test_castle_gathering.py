"""game/train.py and game/gather.py: the lumber camp researches Bow Saw (villagers chop wood 20 % faster, 150 food,
100 wood, 50 s) and the mining camp Gold Shaft Mining and Stone Shaft Mining (gold or stone 15 % faster, 175 food,
75 wood, 75 s) in the Castle Age, each after its Feudal Age technology, in its slot (#1423, AoE2 DE wiki infoboxes)."""
from urllib.parse import unquote

import pytest
from test_gather import FakeServer, grid

from game import gather, train

LINES = [("BOW_SAW", "DOUBLE_BIT_AXE", "LUMBER_CAMP", "Bow Saw", "150 food · 100 wood · 50 s", "wood", 1.2),
         ("GOLD_SHAFT_MINING", "GOLD_MINING", "MINING_CAMP", "Gold Shaft Mining", "175 food · 75 wood · 75 s", "gold", 1.15),
         ("STONE_SHAFT_MINING", "STONE_MINING", "MINING_CAMP", "Stone Shaft Mining", "175 food · 75 wood · 75 s", "stone", 1.15)]


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


@pytest.mark.parametrize("tech, before, camp, label, cost, res, rate", LINES)
def test_the_menu_shows_the_castle_technology_after_its_feudal_technology_in_its_slot(tech, before, camp, label, cost, res, rate):
    slot = train.ITEMS[before][0]
    assert train.ITEMS[tech][0] == slot and train.BY_KEY["after"][tech] == before
    assert tech in train.TRAINS[camp]
    server, g = setup(camp)
    train.open_menu(g, "Steve", (3, 3))
    assert f":book:{label}:" not in menus(server)[-1] and train.queue(g, "Steve", (3, 3), tech) is None
    server, g = setup(camp, before)
    train.open_menu(g, "Steve", (3, 3))
    assert f" {slot}:book:{label}:{cost} · research " in menus(server)[-1] + " "
    server, g = setup(camp, before)                                # the Feudal Age: not yet
    g.techs.discard("CASTLE_AGE")
    assert train.queue(g, "Steve", (3, 3), tech) is None


@pytest.mark.parametrize("tech, before, camp, label, cost, res, rate", LINES)
def test_after_the_research_the_villagers_gather_faster(tech, before, camp, label, cost, res, rate):
    server, g = setup(camp, before)
    old = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, train.ITEMS[tech][0]) == 1
    assert (g.stock["food"], g.stock["wood"]) == (500 - train.COSTS[tech]["food"], 500 - train.COSTS[tech]["wood"])
    train.tick(g, train.TRAIN_TIMES[tech])
    assert tech in g.techs
    assert g.work_time(res) == pytest.approx(old[res] / rate)
    assert {r: g.work_time(r) for r in old if r != res} == {r: t for r, t in old.items() if r != res}
    train.open_menu(g, "Steve", (3, 3))
    assert label not in menus(server)[-1]
