"""Hideout: a forest base terrain with a clearing per player; each DE forest terrain gets its trees (#5381)."""
import numpy as np
import pytest
from AoE2ScenarioParser.datasets.terrains import TerrainId

import rmap

HIDEOUT = """#const MY_FOREST %d
<LAND_GENERATION>
base_terrain MY_FOREST
create_player_lands { terrain_type GRASS land_percent 10 base_size 8 }
"""
FORESTS = [t.value for t in TerrainId if t.name.startswith("FOREST_") and "REEDS" not in t.name]


@pytest.mark.parametrize("forest", FORESTS)
def test_a_forest_map_with_a_clearing_per_player(forest):
    d = rmap.generate(HIDEOUT % forest, 1, players=2, size=60, warn=lambda m: pytest.fail(m))
    terrain = np.array(d["terrain"])
    trees = {(int(o["x"]), int(o["y"])) for o in d["objects"] if "TREE" in o["name"]}
    assert trees == {tuple(map(int, c)) for c in np.argwhere(terrain == forest)}    # a tree on each forest tile
    assert len(trees) > terrain.size // 2                                           # mostly forest
    for st in d["lands"]:
        assert terrain[st["x"], st["y"]] == rmap.TERRAINS["GRASS"]                  # each start in a clearing
