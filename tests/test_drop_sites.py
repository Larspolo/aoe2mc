"""game/gather.py: each resource goes to its own drop sites, as in AoE2 (#389). A small aoe2mc.json dict, no server."""
from game import gather


def building(name, x0, z0, size=4, player=1):
    return {"kind": "building", "name": name, "player": player, "footprint": [x0, z0, x0 + size, z0 + size]}


def data(*objects):
    return {"tile_size": 1, "ground": [" ".join(["64"] * 40) for _ in range(40)], "objects": list(objects)}


class Server:
    def __init__(self):
        self.log = []

    def command(self, cmd):
        self.log.append(cmd)
        return ""


def test_drop_sites_per_resource():
    m = gather.Map(data(building("TOWN_CENTER", 30, 30), building("LUMBER_CAMP", 4, 4), building("MILL", 10, 4),
                        building("MINING_CAMP", 16, 4), building("LUMBER_CAMP", 22, 4, player=2)))
    cells = lambda x0, z0: {(x, z) for x in range(x0, x0 + 4) for z in range(z0, z0 + 4)}  # noqa: E731
    assert m.drops["wood"] == [cells(30, 30), cells(4, 4)]               # the order of the objects
    assert sorted(map(min, m.drops["food"])) == [(10, 4), (30, 30)]
    assert m.drops["gold"] == m.drops["stone"] and sorted(map(min, m.drops["gold"])) == [(16, 4), (30, 30)]
    assert cells(22, 4) not in m.drops["wood"]                         # the camp of player 2


def test_a_villager_with_wood_walks_to_the_nearest_wood_site():
    """The mill and the mining camp are nearer, but they do not take wood: the villager goes to the lumber camp."""
    d = data(building("TOWN_CENTER", 30, 30), building("MILL", 4, 0), building("MINING_CAMP", 4, 10),
             building("LUMBER_CAMP", 14, 4))
    server = Server()
    g = gather.Gather(server, d, start={})
    v = g.villagers["v"] = gather.Villager("v", (2.5, 64.0, 7.5))
    v.state, v.load, v.tree = "to_drop", 0, None
    g.go(v, "to_drop", set().union(*map(g.map.around, g.map.drops[v.res])))
    end = v.path[-1]
    assert end in g.map.around(g.map.drops["wood"][1]) and v.res == "wood"
    v.load = 7
    for _ in range(len(v.path) + 1):
        g.step()
    assert g.stock == {"wood": 7, "food": 0, "gold": 0, "stone": 0} and g.wood == 7
    assert "scoreboard players add Wood aoe_res 7" in server.log
