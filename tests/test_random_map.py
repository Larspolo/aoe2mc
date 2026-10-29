"""--random-map arabia: an own generator of the land and the start objects, with no game file (#993)."""
from collections import Counter

import numpy as np
import pytest

import aoe2mc
import rmap


def test_arabia_gives_grass_dirt_forests_and_the_start_objects_of_each_player():
    d = rmap.random_map("arabia", 7)
    t = np.array(d["terrain"])
    kinds = set(np.unique(t).tolist())
    assert {rmap.TERRAINS["GRASS"], rmap.TERRAINS["DIRT"], rmap.TERRAINS["FOREST"]} <= kinds
    assert kinds <= {rmap.TERRAINS[k] for k in ("GRASS", "DIRT", "DIRT3", "GRASS3", "FOREST", "WATER")}
    n = Counter((o["name"], o.get("player", 0)) for o in d["objects"])
    own = [(name, count) for name, count, _, player in rmap.START if player]   # the start objects of each player
    villagers = sum(count for name, count in own if name.startswith("VILLAGER"))
    for p in (1, 2):
        assert n["TOWN_CENTER", p] == 1 and all(n[name, p] == count for name, count in own if not name.startswith("VILLAGER"))
        assert n["VILLAGER_MALE", p] + n["VILLAGER_FEMALE", p] == villagers
    assert n["GOLD_MINE", 0] and n["STONE_MINE", 0] and n["FORAGE_BUSH", 0] and n["DEER", 0] and n["WILD_BOAR", 0]
    for o in d["objects"]:                     # no start object on a forest or water tile
        if not o["name"].startswith("TREE"):
            assert t[int(o["x"]), int(o["y"])] in (0, 3, 6, 9), o


def test_the_players_stand_on_a_circle_far_from_each_other():
    tc = [o for o in rmap.random_map("arabia", 3)["objects"] if o["name"] == "TOWN_CENTER"]
    assert len(tc) == 2 and np.hypot(tc[0]["x"] - tc[1]["x"], tc[0]["y"] - tc[1]["y"]) > 60


def test_the_same_seed_gives_the_same_map_and_another_seed_another():
    assert rmap.random_map("arabia", 5) == rmap.random_map("arabia", 5)
    assert rmap.random_map("arabia", 5)["terrain"] != rmap.random_map("arabia", 6)["terrain"]


def test_read_map_reads_the_random_map_source():
    size, terrain, elevation, _, _, objects, players = aoe2mc.read_map(aoe2mc.RANDOM_MAP + "arabia", 7)
    assert size == 120 and terrain.shape == (120, 120) and elevation.any()  # hills, #3824
    assert sum(o["name"] == "TOWN_CENTER" for o in objects) == 2 and {1, 2} <= set(players)


def test_random_map_takes_only_the_output_folder(capsys):
    with pytest.raises(SystemExit):
        aoe2mc.main(["--random-map", "arabia", "IN.aoe2scenario", "OUT"])
    assert "only the output" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        aoe2mc.main(["OUT"])
