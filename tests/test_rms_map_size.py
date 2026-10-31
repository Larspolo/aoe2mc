"""--map-size: the lobby size of a random map script (#4823)."""
import numpy as np
import pytest

import aoe2mc
import rmap

SCRIPT = """<LAND_GENERATION>
if LUDIKRIS_MAP
base_terrain DESERT
elseif TINY_MAP
base_terrain SNOW
else
base_terrain GRASS
endif
"""


@pytest.fixture
def script(tmp_path):
    p = tmp_path / "sizes.rms"
    p.write_text(SCRIPT)
    return str(p)


@pytest.mark.parametrize("name, terrain", [("ludikris", "DESERT"), ("tiny", "SNOW")])
def test_size_name_gives_side_and_label(script, name, terrain):
    size, grid = aoe2mc.read_rms(script, 1, 2, size=aoe2mc.map_size(name))[:2]
    assert size == rmap.MAP_SIZES[name]
    assert np.all(grid == rmap.TERRAINS[terrain])


def test_number_is_tiles():
    assert aoe2mc.map_size("150") == 150


def test_wrong_name_lists_names(capsys):
    with pytest.raises(SystemExit):
        aoe2mc.main(["x.rms", "out", "--map-size", "huge2"])
    err = capsys.readouterr().err
    assert all(n in err for n in rmap.MAP_SIZES)


def test_script_size_only_without_option(tmp_path):
    p = tmp_path / "o.rms"
    p.write_text("<PLAYER_SETUP>\noverride_map_size 100\n" + SCRIPT)
    assert aoe2mc.read_rms(str(p), 1)[0] == 100
    assert aoe2mc.read_rms(str(p), 1, size=144)[0] == 144
