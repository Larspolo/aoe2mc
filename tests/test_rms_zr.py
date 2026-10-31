"""A ZR@ random map: a zip archive of the script and its files, read as the script in a folder (#5404)."""
import zipfile

import numpy as np

import aoe2mc
import rmap

SCRIPT = """#include_drs inc/a.inc
<LAND_GENERATION>
base_terrain MY_LAND
if LABEL
  create_land { terrain_type WATER number_of_tiles 40 land_position 50 50 }
endif
"""
INCLUDE = f"#const MY_LAND {rmap.TERRAINS['DIRT']}\n#define LABEL\n"


def test_a_zip_archive_gives_the_terrain_of_its_extracted_script(tmp_path):
    archive = tmp_path / "ZR@small.rms"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("small.rms", SCRIPT)
        z.writestr("inc/a.inc", INCLUDE)
    folder = tmp_path / "plain"
    (folder / "inc").mkdir(parents=True)
    (folder / "small.rms").write_text(SCRIPT)
    (folder / "inc" / "a.inc").write_text(INCLUDE)

    terrain = aoe2mc.read_rms(str(archive), 1)[1]
    assert np.array_equal(terrain, aoe2mc.read_rms(str(folder / "small.rms"), 1)[1])
    assert (terrain == rmap.TERRAINS["DIRT"]).any() and (terrain == rmap.TERRAINS["WATER"]).any()


def test_a_plain_text_zr_file_reads_as_text(tmp_path):
    p = tmp_path / "ZR@x.rms"
    p.write_text("<LAND_GENERATION>\nbase_terrain DESERT\n")
    assert np.all(aoe2mc.read_rms(str(p), 1)[1] == rmap.TERRAINS["DESERT"])
