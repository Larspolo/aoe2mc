"""game/gather.py: 2 or more selected military units that walk to a point end in the AoE2 line formation (#3414):
rows across the walk direction, the melee units in front and the ranged units behind (gather.rank, the unit order of
the AoE2 wiki "Unit formation"). The geometry is replay.formation_cells, the same as the formations of the live replay."""
from test_gather import FakeServer, grid

from game import gather, replay


def setup(units):
    """A flat 32 × 32 map (tile size 1) with the own units {uuid: (name, x, z)}."""
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [x + 0.5, z + 0.5]} for u, (n, x, z) in units.items()]
    server = FakeServer({o["uuid"]: {"Pos": (o["tile"][0], 64.0, o["tile"][1])} for o in objects})
    g = gather.Gather(server, grid([[64] * 32 for _ in range(32)], objects)).setup()
    g.paper = True
    return server, g


def test_the_militia_walk_in_front_of_the_archers():
    archers = {f"a{k}": ("ARCHER", 14 + k, 23) for k in range(4)}            # the archers walk in front of the militia
    militia = {f"m{k}": ("MILITIA", 14 + k, 25) for k in range(4)}
    server, g = setup(archers | militia)
    g.choose(set(archers) | set(militia), "m0")
    out = g.walk_to("Steve", (15, 13))                                       # 10 tiles north
    assert set(out) == set(archers) | set(militia) and len(set(out.values())) == 8   # one unit per cell
    assert max(out[u][1] for u in militia) < min(out[u][1] for u in archers)    # the archers behind the militia
    assert all(abs(out[u][1] - 13) <= 1 for u in militia)                    # the first row on the point
    assert all(abs(out[u][1] - 13 - replay.FORMATION) <= 1 for u in archers)  # the second row


def test_the_rank_follows_the_aoe2_unit_order():
    assert [gather.rank(n) for n in ("KNIGHT", "MILITIA", "ARCHER", "CAVALRY_ARCHER", "HAND_CANNONEER", "MANGONEL",
                                      "MONK")] == [0, 1, 2, 2, 3, 4, 4]


def test_one_unit_and_villagers_take_the_nearest_free_cells():
    server, g = setup({"m0": ("MILITIA", 14, 25), "v0": ("VILLAGER_MALE", 15, 25), "v1": ("VILLAGER_MALE", 16, 25)})
    g.choose({"m0", "v0", "v1"}, "m0")
    assert g.walk_to("Steve", (15, 13)) == {"m0": (15, 13), "v0": (14, 13), "v1": (15, 12)}
