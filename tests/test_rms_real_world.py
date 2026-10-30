"""A real world map script with no <LAND_GENERATION> takes the land of its base scenario (#4729)."""
import numpy as np

import aoe2mc
import rmap
import scenarios

SCRIPT = "<OBJECTS_GENERATION>\ncreate_object TOWN_CENTER { set_place_for_every_player max_distance_to_players 0 }\n"


def test_base_scenario(tmp_path):
    scenarios.tiny(str(tmp_path / "real_world_test.aoe2scenario"))
    size, terrain, elevation, _, _, objects, _ = aoe2mc.read_map(str(tmp_path / "real_world_test.aoe2scenario"))
    warns = []
    d = rmap.generate(SCRIPT, 1, players=1, warn=warns.append, folder=str(tmp_path), name="real_world_test.rms")
    assert d["size"] == size
    assert (np.array(d["terrain"]) == terrain).all()
    assert (np.array(d["elevation"]) >= elevation).all() and np.array(d["elevation"]).max() == elevation.max()
    tc = next(o for o in objects if o["name"] == "TOWN_CENTER")
    assert [(st["player"], st["x"], st["y"]) for st in d["lands"]] == [(tc["player"], int(tc["x"]), int(tc["y"]))]
    assert not any("base scenario" in w for w in warns)


def test_no_base_scenario(tmp_path):
    warns = []
    rmap.generate(SCRIPT, 1, players=1, warn=warns.append, folder=str(tmp_path), name="real_world_test.rms")
    assert [w for w in warns if "base scenario" in w] == [
        "no <LAND_GENERATION> and no base scenario: give real_world_test.scx or real_world_test.aoe2scenario of the "
        "game next to the script"]
