"""The start views of the four_civs scenario: each player has a view 5 tiles in front of its town center."""
import contextlib
import io

import scenarios
import world_reader

import aoe2mc

TOWN_CENTERS = {1: (17, 17), 2: (63, 17), 3: (17, 63), 4: (63, 63)}


def test_each_player_has_a_start_view_in_front_of_its_town_center(tmp_path):
    players = aoe2mc.read_scenario(scenarios.four_civs(str(tmp_path / "s.aoe2scenario")))[6]
    for pid, (tx, ty) in TOWN_CENTERS.items():
        x, y = players[pid]["view"]
        assert 0 <= x < 80 and 0 <= y < 80
        assert max(abs(x - tx), abs(y - ty)) == 5               # 5 tiles from the town center, not on it


def test_the_spawn_is_at_the_view_of_player_one(tmp_path):
    src = scenarios.four_civs(str(tmp_path / "s.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([src, str(tmp_path / "W"), "--mc-version", "26.3"])
    spawn = world_reader.World(str(tmp_path / "W")).level()["spawn"]
    x, z = (int(v) for v in spawn["pos"][::2])
    assert abs(x - 22 * 4) <= 4 and abs(z - 22 * 4) <= 4      # the view tile (22, 22), or the free land next to it
