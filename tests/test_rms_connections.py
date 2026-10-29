"""<CONNECTION_GENERATION> of a random map script: paths of replaced terrain between the player lands (#3868)."""
from collections import deque

import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain WATER
create_player_lands { terrain_type GRASS land_percent 20 base_size 6 }
"""
FORDS = LAND + "<CONNECTION_GENERATION>\ncreate_connect_all_players_land {\n  replace_terrain WATER SHALLOW\n%s}\n"
W, S = rmap.TERRAINS["WATER"], rmap.TERRAINS["SHALLOW"]


def reach(ok, a):
    """The tiles that a 4-step walk on the ok tiles reaches from tile a."""
    seen, todo = {a}, deque([a])
    while todo:
        x, y = todo.popleft()
        for c in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= c[0] < len(ok) and 0 <= c[1] < len(ok) and ok[c] and c not in seen:
                seen.add(c)
                todo.append(c)
    return seen


@pytest.mark.parametrize("players", [2, 4])
def test_the_shallows_join_all_player_lands(players):
    for text, joined in ((FORDS % "", True), (LAND, False)):
        d = rmap.generate(text, 3, players=players, size=80, warn=lambda m: pytest.fail(m))
        t, o = np.array(d["terrain"]), [(st["x"], st["y"]) for st in d["lands"]]
        seen = reach(t != W, o[0])
        assert all(c in seen for c in o[1:]) == joined


def test_terrain_size_widens_the_shallows():
    narrow = np.array(rmap.generate(FORDS % "", 3, size=80)["terrain"]) == S
    t = np.array(rmap.generate(FORDS % "terrain_size WATER 2 0\n", 3, size=80)["terrain"])
    assert narrow.any() and (t[narrow] == S).all()
    for x, y in np.argwhere(narrow):           # a 5 × 5 square around each tile of the path has no water left
        assert not (t[max(0, x - 2):x + 3, max(0, y - 2):y + 3] == W).any()
    assert (t == S).sum() >= 4 * narrow.sum()


def test_a_path_avoids_a_terrain_of_cost_0():
    text = FORDS.replace("<CONNECTION", "<TERRAIN_GENERATION>\ncreate_terrain FOREST { base_terrain WATER "
                         "number_of_tiles 1500 number_of_clumps 6 }\n<CONNECTION") % "terrain_cost FOREST 0\n"
    plain = np.array(rmap.generate(text.replace("<CONNECTION_GENERATION>", "<X>"), 3, size=80, warn=lambda m: 0)["terrain"])
    t = np.array(rmap.generate(text, 3, size=80, warn=lambda m: pytest.fail(m))["terrain"])
    forest = plain == rmap.TERRAINS["FOREST"]
    assert forest.any() and (t == S).any() and not (forest & (t == S)).any() and (t[forest] == rmap.TERRAINS["FOREST"]).all()


def test_the_same_seed_gives_the_same_terrain():
    text = FORDS % "terrain_size WATER 2 1\n"
    assert rmap.generate(text, 9, size=80)["terrain"] == rmap.generate(text, 9, size=80)["terrain"]
