"""A broken random map script gives an RmsError that names the command, not a Python IndexError (#4697)."""
import pytest

import rmap

LAND = "<LAND_GENERATION>\nbase_terrain GRASS\n"


@pytest.mark.parametrize("script, name", [
    (LAND + "if", "if"),
    (LAND + "start_random\npercent_chance", "percent_chance"),
    (LAND + "#define", "#define"),
    (LAND + "#include_drs", "#include_drs"),
    (LAND + "else\nendif", "else"),
    (LAND + "elseif A\nendif", "elseif"),
    (LAND + "percent_chance 50\nend_random", "percent_chance"),
    ("<LAND_GENERATION>\nbase_terrain\n", "base_terrain"),
    (LAND + "create_land { terrain_type GRASS land_percent assign_to_player 1 }\n", "land_percent"),
    (LAND + "create_land { terrain_type GRASS land_percent 10 assign_to AT_PLAYER }\n", "assign_to"),
])
def test_a_missing_word_or_block_gives_an_rms_error_with_the_command(script, name):
    with pytest.raises(rmap.RmsError, match=name):
        rmap.generate(script, 1, warn=lambda m: None)
