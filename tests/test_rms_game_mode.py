"""--game-mode defines the label of the game mode in a random map script (#4824)."""
import numpy as np
import pytest

import aoe2mc
import rmap
from game import run

SCRIPT = "<LAND_GENERATION>\nbase_terrain GRASS\nif REGICIDE\nbase_terrain DESERT\nendif\n"


def terrain(mode, seed=3):
    return np.array(rmap.generate(SCRIPT, seed, warn=lambda m: None, mode=mode)["terrain"])


def test_the_mode_label_gives_its_terrain_only_in_that_mode():
    assert (terrain("regicide") == rmap.TERRAINS["DESERT"]).all()
    for mode in ("standard", "death-match"):
        assert (terrain(mode) == rmap.TERRAINS["GRASS"]).all()
    assert (terrain("regicide") == terrain("regicide")).all()


def test_the_modes_are_the_modes_of_the_game_program():
    assert set(run.MODES) - {"scenario"} | {"king-of-the-hill"} == set(rmap.MODE_LABELS)   # scenario: no lobby mode


def test_a_wrong_mode_lists_the_modes(tmp_path, capsys):
    (tmp_path / "a.rms").write_text(SCRIPT, encoding="utf-8")
    with pytest.raises(SystemExit):
        aoe2mc.main([str(tmp_path / "a.rms"), str(tmp_path / "W"), "--game-mode", "nope"])
    assert "regicide" in capsys.readouterr().err
