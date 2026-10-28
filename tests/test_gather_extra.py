"""game/gather.py: the gather bonuses of the Athenians, Thracians and Varangians (AoE2 DE wiki, #2308). Athenian
lumberjacks earn food 1 for each wood 14.7 (civs.EXTRA), Thracian hunters and shepherds earn gold 3 for each minute of
work at an animal (civs.PER_MINUTE), Varangian hunters, shepherds and fishermen drop off gold 10 % of the food, their
fishing ships 5 % (civs.DROP_EXTRA)."""
import pytest
from test_drop_bonus import game
from test_second_resource import loads
from test_ship_gather import fish_map

from game import civs, fleet, gather


def test_athenian_lumberjacks_earn_food_1_for_each_wood_14_7():
    g, side = loads("ATHENIANS", "wood")
    assert g.stock["wood"] >= 100
    assert g.stock["food"] == side["food"] == pytest.approx(g.stock["wood"] / 14.7, abs=1)
    _, side = loads("ATHENIANS", "stone", n=2)                         # a miner: no food
    assert side["food"] == 0


def test_varangian_food_loads_of_animals_and_fish_give_gold():
    for kind, gold in (("hunt", 2), ("fish", 2), ("ship", 1), (None, 0)):
        g = game("VARANGIANS")
        g.deliver("food", 10, kind=kind)
        g.deliver("food", 10, kind=kind)
        assert g.stock["food"] == 20 and g.stock["gold"] == gold, kind
    g = game("BRITONS")
    g.deliver("food", 10, kind="hunt")
    assert g.stock["gold"] == 0 and g.spare.get("gold", 0) == 0


def drop(civ, where):
    """A villager with a full load of food of a carcass, a shore fish or a fruit bush at the town center."""
    g = game(civ)
    getattr(g.map, where)[(5, 5)] = 100
    v = g.villagers["v"] = gather.Villager("v", (31.5, 64.0, 34.5))
    v.state, v.res, v.load, v.tree, v.path = "to_drop", "food", 10, (5, 5), []
    g.step()
    assert v.load == 0
    return g


def test_a_varangian_hunter_and_fisherman_drop_off_gold():
    for where in ("carcasses", "fish"):
        g = drop("VARANGIANS", where)
        assert g.stock["food"] == 10 and g.stock["gold"] == 1, where       # 10 % of 10 food
    assert drop("VARANGIANS", "bushes").stock["gold"] == 0              # a forager: no gold
    assert drop("SPANISH", "carcasses").stock["gold"] == 0


def test_a_varangian_fishing_ship_drops_off_gold_5_percent():
    server, g, uuid = fish_map()
    g.data["players"]["1"]["civ"] = "VARANGIANS"
    v = g.ships[uuid]
    fleet.fish(g, {uuid}, (20, 12))
    for _ in range(800):
        fleet.tick(g, 0.25)
        if v.state == "to_drop" and not v.path:
            break
    fleet.tick(g, 0.25)
    assert g.spare["gold"] == pytest.approx(15 * 0.05)                 # a load of 15 food


def work(civ, where, seconds=120):
    """Gold of a villager that gathers food for `seconds` real seconds at a carcass (or a fruit bush) with a large load."""
    g = game(civ)
    g.carry = 10000
    getattr(g.map, "carcasses" if where == "herds" else where)[(5, 5)] = 10000
    if where == "herds":
        g.map.herds.add((5, 5))
    v = g.villagers["v"] = gather.Villager("v", (5.5, 64.0, 6.5))
    v.state, v.res, v.load, v.tree, v.path, v.timer = "chop", "food", 0, (5, 5), [], 0.0
    for _ in range(round(seconds / g.tick)):
        g.step()
    assert v.state == "chop" and v.load > 0
    return g.stock["gold"] + g.seconds.get("gold", 0)


def test_thracian_hunters_and_shepherds_earn_gold_3_for_each_minute():
    minutes = 120 * gather.NORMAL / 60                                 # real seconds at Normal speed (#413)
    assert work("THRACIANS", "carcasses") == pytest.approx(3 * minutes)
    assert work("THRACIANS", "herds") == pytest.approx(3 * minutes)   # a sheep
    assert work("THRACIANS", "bushes") == 0                           # a forager: no gold
    assert work("BRITONS", "carcasses") == 0
    assert civs.per_minute(game("THRACIANS"), "wood") is None
