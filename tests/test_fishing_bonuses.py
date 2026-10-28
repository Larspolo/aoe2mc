"""game/civs.py: the fishing and dock bonuses of the Dravidians, Japanese, Malay and Achaemenids (AoE2 DE wiki, #2333).
Fake server, no Minecraft."""
import pytest
from test_civ_work import setup
from test_civ_work_rate import game
from test_gather import grid
from test_ship_gather import fish_map, play

from game import civs, fleet, gather, train

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def ships(civ, age=0):
    server, g, uuid = fish_map()
    g.data["players"]["1"]["civ"] = civ
    g.techs.update(AGES[:age])
    return g, uuid


def test_a_dravidian_fisherman_carries_25_food_and_a_dravidian_forager_10():
    g = setup("DRAVIDIANS")
    assert g.limit("food", "fish") == 25 and g.limit("food", "forage") == 10 and g.limit("wood") == 10
    assert setup("FRANKS").limit("food", "fish") == 10


def test_a_dravidian_fisherman_stops_with_25_food_at_a_shore_fish():
    for civ, load in (("DRAVIDIANS", 25), ("FRANKS", 10)):
        g = setup(civ)
        v = g.villagers["v"]
        g.map.fish[(4, 4)] = 100
        v.res, v.tree, v.state = "food", (4, 4), "chop"
        for _ in range(5000):
            if v.state != "chop":
                break
            g.step()
        assert v.state != "chop" and v.load == load, civ


def test_a_dravidian_fishing_ship_carries_30_food_and_a_briton_one_15():
    g, uuid = ships("DRAVIDIANS")
    assert fleet.carry(g) == 30 and fleet.carry(ships("BRITONS")[0]) == fleet.CARRY == 15
    assert fleet.carry(ships("AZTECS")[0]) == 15                      # the Aztec bonus is for villagers only
    v = g.ships[uuid]
    fleet.fish(g, {uuid}, (20, 12))
    most = 0
    for _ in range(800):                                              # 200 s: it sails there and fills its load
        play(g, 0.25)
        most = max(most, v.load)
    assert most == 30


@pytest.mark.parametrize("age, factor", [(0, 1.05), (1, 1.1), (2, 1.15), (3, 1.2)])
def test_a_japanese_fishing_ship_works_faster_in_each_age(age, factor):
    g, base = ships("JAPANESE", age)[0], ships("BRITONS", age)[0]
    for fish in ((20, 12), (14, 3)):                                  # a deep fish and a shore fish
        assert fleet.rate(g, fish) == pytest.approx(fleet.rate(base, fish) * factor)
    assert civs.ship_work(base) == 1


def test_a_malay_fish_trap_has_3_times_the_food():
    def trap(civ):
        data = grid([[64] * 4 + ["-"] * 8 for _ in range(12)],
                    [{"kind": "building", "name": "FISH_TRAP", "player": 1, "tile": [6.5, 6.5], "footprint": [5, 5, 8, 8]}])
        data["players"] = {"1": {"civ": civ}}
        return gather.Map(data, 1).fish[6, 6]
    assert trap("MALAY") == 3 * gather.TRAP_FOOD == 2145 and trap("BRITONS") == gather.TRAP_FOOD


@pytest.mark.parametrize("age", range(4))
def test_an_achaemenid_dock_trains_15_percent_faster(age):
    _, g = game("ACHAEMENIDS", age)
    assert train.seconds(g, "FISHING_SHIP", "DOCK") == pytest.approx(train.TRAIN_TIMES["FISHING_SHIP"] / 1.15)
    assert train.seconds(g, "VILLAGER_MALE", "TOWN_CENTER") == 25
    _, base = game("BRITONS", age)
    assert train.seconds(base, "FISHING_SHIP", "DOCK") == train.TRAIN_TIMES["FISHING_SHIP"]
