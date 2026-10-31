"""rmap.py: the land of a random map script (#963). The script here is an own small text in the RMS language, not a
script of the game."""
import math

import numpy as np
import pytest

import aoe2mc
import rmap

SCRIPT = """
/* An open land of grass and dirt with small forests and ponds. */
#const MY_DIRT 6
<PLAYER_SETUP>
random_placement
<LAND_GENERATION>
base_terrain DIRT
create_player_lands {
  terrain_type GRASS
  land_percent 40
  base_size 8
  clumping_factor 15
}
start_random
  percent_chance 50
  #define WET
end_random
if WET
  create_land { terrain_type WATER number_of_tiles 60 base_size 2 land_position 50 50 }
endif
<TERRAIN_GENERATION>
create_terrain FOREST {
  base_terrain GRASS
  number_of_clumps 6
  number_of_tiles 240
  set_avoid_player_start_areas
  spacing_to_other_terrain_types 1
}
create_terrain FOREST {
  base_terrain MY_DIRT
  number_of_clumps 4
  number_of_tiles 120
}
<OBJECTS_GENERATION>
create_object TOWN_CENTER { set_place_for_every_player }
"""


def make(seed, players=2, script=SCRIPT):
    notes = []
    return rmap.generate(script, seed, players, warn=notes.append), notes


def test_the_same_seed_gives_the_same_map_and_another_seed_another():
    a, b, c = make(5)[0], make(5)[0], make(6)[0]
    assert a == b
    assert a["terrain"] != c["terrain"]


def test_the_player_lands_are_on_a_circle_without_forest():
    for players in (2, 4):
        d, _ = make(3, players)
        n, t = d["size"], np.array(d["terrain"])
        mid = (n - 1) / 2
        dist = [math.dist((s["x"], s["y"]), (mid, mid)) for s in d["lands"]]
        assert len(dist) == players and max(dist) - min(dist) < 1.5 and min(dist) > n / 4
        for s in d["lands"]:
            r = s["base_size"]
            assert (t[s["x"] - r:s["x"] + r + 1, s["y"] - r:s["y"] + r + 1] == rmap.TERRAINS["GRASS"]).all()
            near = t[max(0, s["x"] - rmap.AVOID):s["x"] + rmap.AVOID + 1, max(0, s["y"] - rmap.AVOID):s["y"] + rmap.AVOID + 1]
            assert not (near == rmap.TERRAINS["FOREST"]).any()      # set_avoid_player_start_areas
        assert (t == rmap.TERRAINS["FOREST"]).sum() > 200               # the forests are there
        assert (t == rmap.TERRAINS["DIRT"]).sum() > 1000                 # the base terrain between the lands


def test_a_random_branch_and_an_if_take_one_way():
    wet = [(np.array(make(s)[0]["terrain"]) == rmap.TERRAINS["WATER"]).any() for s in range(12)]
    assert any(wet) and not all(wet)


def test_unread_sections_and_attributes_give_a_warning():
    _, notes = make(1)
    assert "<OBJECTS_GENERATION> is not read yet" not in notes        # create_object: #3855
    assert "random_placement is not read yet" not in notes            # PLAYER_SETUP: nothing to do here
    _, notes = make(1, script="<LAND_GENERATION> create_land { terrain_type WATER no_such_attribute 3 }")
    assert notes == ["create_land: no_such_attribute is not read yet"]


def test_errors_name_the_problem():
    for text, msg in (("<LAND_GENERATION> base_terrain", "too few arguments"),):
        with pytest.raises(rmap.RmsError, match=msg):
            rmap.generate(text, 1)


def test_read_map_takes_a_script(tmp_path):
    path = tmp_path / "Open.rms"
    path.write_text(SCRIPT)
    size, terrain, elevation, names, _, objects, players = aoe2mc.read_map(str(path), seed=5)
    assert size == 120 and terrain.shape == (120, 120) and not elevation.any()
    forest = {(int(x), int(y)) for x, y in np.argwhere(terrain == rmap.TERRAINS["FOREST"])}
    trees = [o for o in objects if o["name"] != "TOWN_CENTER"]
    assert {(int(o["x"]), int(o["y"])) for o in trees} == forest and {o["name"] for o in trees} == {"TREE_OAK_FOREST"}
    assert sorted(o["player"] for o in objects if o["name"] == "TOWN_CENTER") == [1, 2]
    assert (terrain == np.array(make(5)[0]["terrain"])).all() and names[10] == "FOREST_OAK"
    assert sorted(players) == [0, 1, 2]
    (tmp_path / "Bad.rms").write_text("<LAND_GENERATION> base_terrain")
    with pytest.raises(aoe2mc.OptionError, match="Bad.rms: base_terrain: too few"):
        aoe2mc.read_map(str(tmp_path / "Bad.rms"))
