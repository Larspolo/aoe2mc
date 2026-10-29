"""game/civs.py: the fishing and dock bonuses of the Dravidians, Japanese, Malay and Achaemenids (#2333) are applied: the
expected values come from the civilization keys of game/data/civs.jsonl. Fake server, no Minecraft."""
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


def test_a_fisherman_stops_with_its_load_limit_at_a_shore_fish():
    for civ in ("DRAVIDIANS", "FRANKS"):
        g = setup(civ)
        load = g.limit("food", "fish")
        v = g.villagers["v"]
        g.map.fish[(4, 4)] = 100
        v.res, v.tree, v.state = "food", (4, 4), "chop"
        for _ in range(5000):
            if v.state != "chop":
                break
            g.step()
        assert v.state != "chop" and v.load == load, civ


def test_a_dravidian_fishing_ship_fills_its_load():
    g, uuid = ships("DRAVIDIANS")
    v = g.ships[uuid]
    fleet.fish(g, {uuid}, (20, 12))
    most = 0
    for _ in range(800):                                              # 200 s: it sails there and fills its load
        play(g, 0.25)
        most = max(most, v.load)
    assert most == fleet.carry(g)


@pytest.mark.parametrize("age", range(4))
def test_a_japanese_fishing_ship_works_at_the_rate_of_its_age(age):
    g, base = ships("JAPANESE", age)[0], ships("BRITONS", age)[0]
    for fish in ((20, 12), (14, 3)):                                  # a deep fish and a shore fish
        assert fleet.rate(g, fish) == pytest.approx(fleet.rate(base, fish) * civs.ship_work(g) / civs.ship_work(base))


def test_a_malay_fish_trap_has_the_food_of_its_factor():
    def trap(civ):
        data = grid([[64] * 4 + ["-"] * 8 for _ in range(12)],
                    [{"kind": "building", "name": "FISH_TRAP", "player": 1, "tile": [6.5, 6.5], "footprint": [5, 5, 8, 8]}])
        data["players"] = {"1": {"civ": civ}}
        return gather.Map(data, 1).fish[6, 6]
    for civ in ("MALAY", "BRITONS"):
        assert trap(civ) == round(gather.TRAP_FOOD * civs.value("trap_food", civ, 1)), civ


@pytest.mark.parametrize("age", range(4))
def test_an_achaemenid_dock_trains_faster(age):
    _, g = game("ACHAEMENIDS", age)
    _, base = game("BRITONS", age)
    assert train.seconds(g, "FISHING_SHIP", "DOCK") < train.seconds(base, "FISHING_SHIP", "DOCK")
    assert train.seconds(g, "VILLAGER_MALE", "TOWN_CENTER") == train.seconds(base, "VILLAGER_MALE", "TOWN_CENTER")
