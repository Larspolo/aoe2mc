"""A ZR@ random map with a base scenario gives the map of its extracted folder: land, objects and starts (#5418, #5403)."""
import zipfile

import numpy as np
import scenarios

import aoe2mc

SCRIPT = "<OBJECTS_GENERATION>\ncreate_object TOWN_CENTER { set_place_for_every_player max_distance_to_players 0 }\n"


def same(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, np.ndarray):
        return np.array_equal(a, b)
    return a == b


def test_a_zr_archive_with_a_base_scenario_gives_the_map_of_its_folder(tmp_path, capsys):
    folder = tmp_path / "plain"
    folder.mkdir()
    scenarios.tiny(str(folder / "real_world_test.aoe2scenario"))
    (folder / "real_world_test.rms").write_text(SCRIPT)
    archive = tmp_path / "ZR@real_world_test.rms"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(folder / "real_world_test.rms", "real_world_test.rms")
        z.write(folder / "real_world_test.aoe2scenario", "real_world_test.aoe2scenario")

    capsys.readouterr()
    from_zip = aoe2mc.read_rms(str(archive), 1)
    assert "base scenario" not in capsys.readouterr().err
    from_folder = aoe2mc.read_rms(str(folder / "real_world_test.rms"), 1)

    assert from_zip[0] == from_folder[0]                     # size
    assert np.array_equal(from_zip[1], from_folder[1])       # terrain
    assert np.array_equal(from_zip[2], from_folder[2])       # elevation
    assert same(from_zip, from_folder)                       # objects and players
