"""--players: the player count of a random map script and of --random-map (#3944, #3945)."""
import pytest

import aoe2mc
import rmap


def test_read_map_takes_the_player_count_of_a_random_map(tmp_path):
    size, terrain, _, _, _, objects, players = aoe2mc.read_map(aoe2mc.RANDOM_MAP + "arabia", 1, players=4)
    assert terrain.shape == (rmap.SIZES[4], rmap.SIZES[4])
    assert sum(o["name"] == "TOWN_CENTER" for o in objects) == 4 and {1, 2, 3, 4} <= set(players)


def test_read_map_takes_the_player_count_of_a_script(tmp_path):
    path = tmp_path / "Land.rms"
    path.write_text("<LAND_GENERATION>\nbase_terrain DIRT\n")
    size, terrain, _, _, _, _, players = aoe2mc.read_map(str(path), 1, players=4)
    assert terrain.shape == (rmap.SIZES[4], rmap.SIZES[4]) and {1, 2, 3, 4} <= set(players)


def test_players_is_refused_for_a_scenario(tmp_path):
    with pytest.raises(SystemExit):
        aoe2mc.main([str(tmp_path / "IN.aoe2scenario"), str(tmp_path / "OUT"), "--players", "3"])


def test_players_range_is_checked(capsys):
    with pytest.raises(SystemExit):
        aoe2mc.main(["--random-map", "arabia", "OUT", "--players", "9"])
    assert "--players" in capsys.readouterr().err
