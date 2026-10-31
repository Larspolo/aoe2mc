"""game/per.py: the perimeter facts gate-count and wall-invisible-percentage (airef "Facts", #5091). They take the
perimeter first, as wall-completed-percentage does; the map of test_per_counts."""
from test_per_counts import script

from game.bot import build  # noqa: F401  (the module that per uses)


def test_perimeter_facts_are_true_with_no_exception(capsys):
    s, b, me = script()
    assert s.check(("gate-count", 2, "==", 0))
    assert s.check(("gate-count", 1, ">=", 0))
    assert s.check(("wall-invisible-percentage", 1, "==", 0))
    assert "unknown" not in capsys.readouterr().err


def test_a_gate_inside_perimeter_1_counts():
    s, b, me = script()
    g = b.g
    T, (cx, cz) = g.map.T, b.center()
    x, z = cx // T + 2, cz // T                                          # two tiles from the town center
    g.sites.append({"name": build.GATES[0], "player": g.player, "progress": 1,
                    "footprint": [x * T, (x + 1) * T, z * T, (z + 1) * T]})
    assert s.check(("gate-count", 1, "==", 1)) and s.check(("gate-count", 2, "==", 1))
