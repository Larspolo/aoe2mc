"""A record of an AoE2 DE game on a custom scenario (save 68.9) gives its start state (#5203)."""
import pytest

import aoe2mc

pytest.importorskip("mgz")


def test_a_scenario_game_gives_its_players_and_start_objects():
    size, terrain, _, _, _, objects, players = aoe2mc.read_record("samples/de-trigger-test.aoe2record")
    assert sorted(players) == [0, 1, 2]
    assert terrain.shape == (size, size)
    assert {o["player"] for o in objects} >= {1, 2}
