"""land_conformity and generate_mode of create_land and create_player_lands: no warning (#4423)."""
import pytest

import rmap


@pytest.mark.parametrize("cmd", ["create_land", "create_player_lands"])
def test_land_conformity_and_generate_mode_give_no_warning(cmd):
    text = f"<LAND_GENERATION>\nbase_terrain GRASS\n{cmd} {{ terrain_type DIRT land_percent 10 land_conformity 50 generate_mode 1 }}\n"
    assert rmap.generate(text, 1, size=60, warn=lambda m: pytest.fail(m))["size"] == 60
