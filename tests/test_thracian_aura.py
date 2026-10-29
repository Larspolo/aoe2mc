"""The Thracian forts and towers (#2378): miners and lumberjacks near them work faster, and they take some resources
(game/data/civs.jsonl, key "aura"). A small aoe2mc.json dict, no server."""
from game import civs, gather

T = 4
AURA = civs.AURA["THRACIANS"]
TOWER, RES = AURA["buildings"][0], AURA["resources"][0]


def data(civ, *objects):
    return {"tile_size": T, "ground": [" ".join(["64"] * 100) for _ in range(100)], "objects": list(objects),
            "players": {"1": {"civ": civ}}}


def building(name, tx, tz, size=1, player=1):
    return {"kind": "building", "name": name, "player": player,
            "footprint": [tx * T, tz * T, (tx + size) * T, (tz + size) * T]}


class Server:
    def command(self, cmd):
        return ""


def game(civ, *objects):
    return gather.Gather(Server(), data(civ, building("TOWN_CENTER", 20, 20, 4), *objects), start={})


def miner(g, tx, tz, res="gold"):
    v = g.villagers["v"] = gather.Villager("v", (tx * T + 0.5, 64.0, tz * T + 0.5))
    v.res = res
    return v


def test_a_thracian_miner_near_a_tower_mines_faster_and_drops_there():
    g = game("THRACIANS", building(TOWER, 5, 5))
    tower = {(x, z) for x in range(5 * T, 6 * T) for z in range(5 * T, 6 * T)}
    v = miner(g, 10, 5, RES)                               # 5 tiles from the tower
    for r in ("food", "farm", "gold", "stone", "wood"):    # food: no farmers, foragers or hunters
        assert g.aura_rate(v, r) == (AURA["rate"] if r in AURA["resources"] else 1), r
    assert g.map.around(tower) <= g.drop_goals(v)          # the tower takes the resource
    assert all((tower in g.map.drops[r]) == (r in AURA["resources"]) for r in ("food", "gold", "stone", "wood"))


def test_the_aura_reaches_its_range_from_the_footprint():
    g = game("THRACIANS", building(TOWER, 5, 5, 4))
    edge = 9 + AURA["range"] - 1                           # the last tile in range east of the footprint
    assert g.aura_rate(miner(g, edge, 5, RES), RES) == AURA["rate"]
    assert g.aura_rate(miner(g, edge + 2, 5, RES), RES) == 1


def test_a_frank_miner_near_a_tower_gets_neither():
    g = game("FRANKS", building(TOWER, 5, 5))
    tower = {(x, z) for x in range(5 * T, 6 * T) for z in range(5 * T, 6 * T)}
    v = miner(g, 10, 5, RES)
    assert g.aura_rate(v, RES) == 1 and not g.map.around(tower) & g.drop_goals(v)


def test_an_enemy_tower_gives_no_aura():
    g = game("THRACIANS", building(TOWER, 5, 5, player=2))
    assert g.aura_rate(miner(g, 6, 5, RES), RES) == 1
