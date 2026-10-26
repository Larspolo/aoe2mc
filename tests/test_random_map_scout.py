"""--random-map nomad: 3 villagers and no Scout Cavalry, as AoE2 Nomad; the other kinds keep the scout (#1216)."""
import pytest

import rmap


def scouts(kind, seed, players):
    d = rmap.random_map(kind, seed, players)
    return [o["player"] for o in d["objects"] if o["name"] == "SCOUT_CAVALRY"]


@pytest.mark.parametrize("players", [2, 4])
@pytest.mark.parametrize("seed", range(1, 11))
def test_nomad_has_no_scout(seed, players):
    assert scouts("nomad", seed, players) == []


@pytest.mark.parametrize("kind", sorted(set(rmap.GENERATORS) - set(rmap.NOMADS)))
def test_the_other_kinds_keep_one_scout_for_each_player(kind):
    assert sorted(scouts(kind, 7, 2)) == [1, 2]
