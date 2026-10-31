"""--game-mode works with a ZR@ random map archive as with a plain .rms script (#5419, part of #5403)."""
import json
import zipfile

import numpy as np

import aoe2mc
import rmap

SCRIPT = "<LAND_GENERATION>\nbase_terrain GRASS\nif REGICIDE base_terrain DESERT endif\n"


def make_archive(tmp_path):
    archive = tmp_path / "ZR@mode.rms"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("mode.rms", SCRIPT)
    return archive


def test_the_mode_of_a_zr_archive_gives_its_terrain_only_in_that_mode(tmp_path):
    archive = str(make_archive(tmp_path))
    desert = aoe2mc.read_rms(archive, 3, 2, mode="regicide")[1]
    grass = aoe2mc.read_rms(archive, 3, 2, mode="standard")[1]
    assert (np.array(desert) == rmap.TERRAINS["DESERT"]).all()
    assert (np.array(grass) == rmap.TERRAINS["GRASS"]).all()


def test_a_zr_archive_converts_with_the_game_mode(tmp_path):
    archive = make_archive(tmp_path)
    out = tmp_path / "W"
    aoe2mc.main([str(archive), str(out), "--game-mode", "regicide", "--no-units"])
    assert json.loads((out / "aoe2mc.json").read_text())["lobby"]["mode"] == "regicide"
