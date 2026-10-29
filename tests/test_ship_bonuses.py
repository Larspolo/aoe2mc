"""The hit point bonus of the Portuguese ships (#2290, AoE2 DE) reaches the server: the `aoe stats` command of a
trained galley has the hit points of train.stats."""
from game import train


def test_a_trained_portuguese_galley_gets_the_hit_points_on_the_server():
    from test_civ_units import trained
    g, uuid, log = trained("PORTUGUESE", "GALLEY")
    assert f"aoe stats {uuid} {train.stats(g, 'GALLEY').hp} " in " ".join(log)
