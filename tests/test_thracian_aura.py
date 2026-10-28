"""The Thracian forts and towers (#2378): miners and lumberjacks near them work 15 % faster, and they take wood, gold
and stone (game/data/civs.jsonl, key "aura"). A small aoe2mc.json dict, no server."""
from game import gather

T = 4


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


def test_a_thracian_miner_near_a_watch_tower_mines_faster_and_drops_there():
    g = game("THRACIANS", building("WATCH_TOWER", 5, 5))
    tower = {(x, z) for x in range(5 * T, 6 * T) for z in range(5 * T, 6 * T)}
    v = miner(g, 10, 5)                                    # 5 tiles from the tower
    assert g.aura_rate(v, "gold") == g.aura_rate(v, "stone") == g.aura_rate(v, "wood") == 1.15
    assert g.aura_rate(v, "food") == g.aura_rate(v, "farm") == 1   # no farmers, foragers or hunters
    assert g.map.around(tower) <= g.drop_goals(v)          # the tower takes the gold
    assert all(tower in g.map.drops[r] for r in ("gold", "stone", "wood")) and tower not in g.map.drops["food"]


def test_the_aura_reaches_8_tiles_from_the_footprint():
    g = game("THRACIANS", building("FORTRESS", 5, 5, 4))
    assert g.aura_rate(miner(g, 16, 5), "gold") == 1.15    # in the 8th tile east of the fort
    assert g.aura_rate(miner(g, 18, 5), "gold") == 1


def test_a_frank_miner_near_a_watch_tower_gets_neither():
    g = game("FRANKS", building("WATCH_TOWER", 5, 5))
    tower = {(x, z) for x in range(5 * T, 6 * T) for z in range(5 * T, 6 * T)}
    v = miner(g, 10, 5)
    assert g.aura_rate(v, "gold") == 1 and not g.map.around(tower) & g.drop_goals(v)


def test_an_enemy_tower_gives_no_aura():
    g = game("THRACIANS", building("WATCH_TOWER", 5, 5, player=2))
    assert g.aura_rate(miner(g, 6, 5), "gold") == 1
