"""game/gather.py: a group of military units that walks far (more than replay.FAR_TILES tiles) takes a long column,
2 units across, as in AoE2 (#3417). A walk of 10 tiles keeps the wide line."""
from test_gather import FakeServer, grid

from game import gather


def setup(units, size=64):
    """A flat map of size × size tiles (tile size 1) with the own units {uuid: (name, x, z)}."""
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [x + 0.5, z + 0.5]} for u, (n, x, z) in units.items()]
    server = FakeServer({o["uuid"]: {"Pos": (o["tile"][0], 64.0, o["tile"][1])} for o in objects})
    g = gather.Gather(server, grid([[64] * size for _ in range(size)], objects)).setup()
    g.paper = True
    return server, g


def militia(n=8):
    """n militia in two rows of 4 at the north edge of the map."""
    return {f"m{k}": ("MILITIA", 10 + k % 4, 10 + k // 4) for k in range(n)}


def test_a_far_walk_ends_in_two_columns():
    server, g = setup(militia())
    g.choose(set(militia()), "m0")
    out = g.walk_to("Steve", (15, 50))                                       # 40 tiles south
    assert len(out) == 8 and len(set(out.values())) == 8                     # one unit per cell
    xs = [x for x, _ in out.values()]
    assert max(xs) - min(xs) <= 2                                            # 2 columns across the walk, 1 cell apart
    assert max(z for _, z in out.values()) >= 49                             # the front row on the target


def test_a_near_walk_keeps_the_wide_line():
    server, g = setup(militia())
    g.choose(set(militia()), "m0")
    out = g.walk_to("Steve", (15, 20))                                       # 10 tiles south
    xs = [x for x, _ in out.values()]
    assert len(out) == 8 and max(xs) - min(xs) >= 3                          # rows across the walk, as before


def test_two_units_on_a_far_walk_stand_one_behind_the_other():
    server, g = setup({"m0": ("MILITIA", 10, 10), "m1": ("MILITIA", 11, 10)})
    g.choose({"m0", "m1"}, "m0")
    out = g.walk_to("Steve", (10, 50))
    xs = [x for x, _ in out.values()]
    assert max(xs) - min(xs) <= 1 and len({z for _, z in out.values()}) == 2  # one behind the other
