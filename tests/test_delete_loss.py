"""A deleted own building counts as lost (#3736): it leaves the economy score (score.buildings) and the recap counts
it in "Buildings: N built, M lost" (ruins.fall keeps it in g.fell), also a start building of the map."""
import pytest
from test_own_building_fall import HOUSE, fallen_town, stand

from game import demolish, recap, score

SITE = (20, 22, 14, 16)                                            # a done own house (block footprint x0, x1, z0, z1)


def town():
    server, g, live = fallen_town()
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": list(SITE), "done": True})
    live.update(stand(server, [SITE]))
    return server, g


def own(g):
    return next(p for title, p in recap.parts(g, lambda n: True) if title == f"Player {g.player}")


def test_a_deleted_start_house_leaves_the_economy_score_and_gives_no_military_points():
    server, g = town()
    before = score.points(g, [g])[1]
    assert ("HOUSE", False) in score.buildings(g, set())
    assert demolish.delete(g, "Steve", HOUSE)
    after = score.points(g, [g])[1]
    assert ("HOUSE", False) not in score.buildings(g, set())
    assert after["economy"] == pytest.approx(before["economy"] - 0.2 * score.worth("HOUSE"))
    assert after["military"] == before["military"] and not vars(g).get("razed")


def test_the_recap_counts_a_deleted_start_house_and_a_deleted_own_house_as_lost():
    server, g = town()
    assert "Buildings: 1 built, 0 lost" in own(g)
    assert demolish.delete(g, "Steve", HOUSE) and demolish.delete(g, "Steve", SITE)
    assert "Buildings: 1 built, 2 lost" in own(g)
