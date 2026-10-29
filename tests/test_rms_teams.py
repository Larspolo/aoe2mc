"""The teams of a random map (#3946): grouped_by_team puts the lands of a team next to each other on the circle."""
import numpy as np

import rmap
from game import gather

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT land_percent 40 base_size 4 }
"""
GROUPED = "<PLAYER_SETUP>\ngrouped_by_team\n" + LAND
RANDOM = "<PLAYER_SETUP>\nrandom_placement\n" + LAND
TEAMS = [1, 2, 1, 2]


def order(text, seed, teams=TEAMS):
    """The players in their order around the center of the map."""
    d = rmap.generate(text, seed, len(teams), size=60, warn=lambda m: None, teams=teams)
    c = (d["size"] - 1) / 2
    return [st["player"] for st in sorted(d["lands"], key=lambda st: np.arctan2(st["y"] - c, st["x"] - c))]


def test_grouped_by_team_puts_a_team_together():
    for seed in range(5):
        o = order(GROUPED, seed)
        for a, b in ((1, 3), (2, 4)):
            assert abs(o.index(a) - o.index(b)) in (1, 3), (seed, o)


def test_random_placement_gives_other_orders():
    orders = {tuple(order(RANDOM, seed)) for seed in range(8)}
    rotations = {min(o[i:] + o[:i] for i in range(4)) for o in orders}
    assert len(rotations) > 1


def test_the_map_description_has_the_teams():
    d = rmap.generate(GROUPED, 1, 4, size=60, warn=lambda m: None, teams=[1, 2, 1, None])
    assert [d["players"][str(p)].get("team") for p in range(1, 5)] == [1, 2, 1, None]
    assert gather.allied(d["players"], 1, 3) and not gather.allied(d["players"], 1, 2)
    assert not gather.allied(d["players"], 4, 2)


def test_no_teams_keeps_the_map():
    a = rmap.generate(GROUPED, 3, 2, size=60, warn=lambda m: None)
    b = rmap.generate(LAND, 3, 2, size=60, warn=lambda m: None)
    assert a["lands"] == b["lands"] and a["terrain"] == b["terrain"]
    assert "team" not in a["players"]["1"]
    assert [st["player"] for st in a["lands"]] == [1, 2]
