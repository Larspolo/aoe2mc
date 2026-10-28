"""game/gather.py, game/fleet.py: villagers and fishing ships gather gold from oysters (AoE2 DE wiki "Oysters": 450
gold, villagers 22.8 a minute, fishing ships 24), and the Puru gather from them 15 % faster (#2465)."""
import pytest
from test_build_site import Server
from test_drop_bonus import game
from test_gather import grid

from game import fleet, gather, train


def oyster_map(civ="BRITONS"):
    """Land at x < 14, water at x >= 14, a dock of player 1 at the shore; an oyster at the shore (14, 6), one in the
    water (20, 6) and a salmon at (21, 14)."""
    rows = [[64] * 14 + ["-"] * 10 for _ in range(24)]
    data = grid(rows, [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
                       {"kind": "building", "name": "DOCK", "player": 1, "tile": [15.5, 12.5], "footprint": [14, 11, 17, 14]},
                       {"kind": "other", "name": "OYSTER", "tile": [14.5, 6.5]},
                       {"kind": "other", "name": "OYSTER", "tile": [20.5, 6.5]},
                       {"kind": "other", "name": "FISH_SALMON", "tile": [21.5, 14.5]}])
    data["players"] = {"1": {"civ": civ, "color": "blue", "arch": "western"}}
    data["level_height"] = 1
    server = Server({"Steve": {"Pos": (12.5, 64.0, 12.5), "Rotation": (-90.0, 40.0)}})
    g = gather.Gather(server, data).setup()
    g.stock["wood"] = 200
    rect = train.open_menu(g, "Steve", (15, 12))
    assert train.order(g, "Steve", rect, 0) == 1
    uuid, = train.tick(g, 40)
    return server, g, uuid


def test_an_oyster_is_a_shore_source_of_450_gold():
    _, g, _ = oyster_map()
    assert g.map.oysters == {(14, 6), (20, 6)} and g.map.fish[14, 6] == g.map.fish[20, 6] == 450
    assert (14, 6) in g.map.shore and g.map.resource((14, 6)) == "gold" and g.map.resource((21, 14)) == "food"
    assert gather.job_of(g.map, (14, 6)) == "OYSTER" and gather.job_of(g.map, (21, 14)) == "FISHERMAN"


def gathered(civ, seconds=20):
    """The gold that a villager of civ gathers at an oyster in `seconds` real seconds (a large load)."""
    g = game(civ)
    g.carry = 1000
    g.map.fish[5, 5] = 1000
    g.map.oysters.add((5, 5))
    v = g.villagers["v"] = gather.Villager("v", (5.5, 64.0, 6.5))
    v.state, v.res, v.load, v.tree, v.path, v.timer = "chop", "gold", 0, (5, 5), [], 0.0
    for _ in range(round(seconds / g.tick)):
        g.step()
    assert v.state == "chop"
    return v.load


def test_a_villager_gathers_gold_at_the_oyster_rate_15_percent_faster_for_the_puru():
    assert gathered("BRITONS") == int(20 * gather.NORMAL * 0.38)                    # 22.8 gold per game minute
    assert gathered("MALIANS") == gathered("BRITONS")                               # gold miners: not at an oyster
    assert gathered("PURU") == int(20 * gather.NORMAL * 0.38 * 1.15)


def test_a_villager_sent_to_an_oyster_carries_gold_to_a_gold_drop_site():
    _, g, _ = oyster_map()
    v = g.villagers["v"] = gather.Villager("v", (12.5, 64.0, 6.5))
    g.send((14, 6), {"v"})
    assert v.res == "gold" and v.tree == (14, 6) and v.job == "fisherman"
    v.load = 10
    assert g.drop_goals(v) == set().union(*map(g.map.around, g.map.drops["gold"]))


@pytest.mark.parametrize("civ, carry", [("BRITONS", 10), ("DRAVIDIANS", 25)])
def test_a_dravidian_oyster_gatherer_carries_15_more(civ, carry):
    assert game(civ).limit("gold", "oyster") == carry


def test_a_fishing_ship_gathers_gold_at_an_oyster_and_drops_it_at_the_dock():
    server, g, uuid = oyster_map()
    v, food, gold = g.ships[uuid], g.stock["food"], g.stock["gold"]
    assert fleet.fish(g, {uuid}, (20, 6)) == {uuid} and v.res == "gold"
    assert fleet.rate(g, (20, 6)) == pytest.approx(0.4)                             # 24 gold per game minute
    for _ in range(600):
        fleet.tick(g, 0.25)
        if v.state == "to_drop":
            break
    assert v.load == 15 and g.map.fish[20, 6] == 435
    for _ in range(80):
        fleet.tick(g, 0.25)
        if v.state != "to_drop":
            break
    assert g.stock["gold"] == gold + 15 and g.stock["food"] == food and v.tree == (20, 6)
    assert f"scoreboard players add Gold {g.board} 15" in server.log


def test_a_puru_fishing_ship_gathers_oysters_15_percent_faster():
    _, puru, _ = oyster_map("PURU")
    _, britons, _ = oyster_map()
    assert fleet.rate(puru, (20, 6)) == pytest.approx(fleet.rate(britons, (20, 6)) * 1.15)
    assert fleet.rate(puru, (21, 14)) == pytest.approx(fleet.rate(britons, (21, 14)))   # a fish: no bonus


def test_after_an_empty_oyster_a_ship_takes_the_next_oyster_and_its_pickles_go():
    server, g, uuid = oyster_map()
    assert fleet.nearest(g, (20, 6)) == (20, 6) and fleet.nearest(g, (21, 14)) == (21, 14)
    g.map.fish[20, 6] = 0
    assert fleet.nearest(g, (20, 6)) == (14, 6)                                     # not the nearer salmon
    fleet.remove(g, (20, 6))
    assert (20, 6) not in g.map.oysters and (20, 6) not in g.map.fish
    assert "fill 20 -64 6 20 319 6 minecraft:water replace minecraft:sea_pickle" in server.log
