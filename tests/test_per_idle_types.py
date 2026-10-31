"""up-idle-unit-count with an airef idle type (#5096): idle-type-villager counts as idle-villagers, the other types count
their idle units (0 when the bot has none). The map of test_per_counts: the bot has idle villagers and two militia."""
from test_per_counts import script


def test_idle_type_names_are_known(capsys):
    s, b, me = script()
    assert s.check(("up-idle-unit-count", "idle-type-villager", ">=", 0))
    assert s.check(("up-idle-unit-count", "idle-type-trade-cart", "==", 0))
    assert "unknown" not in capsys.readouterr().err


def test_idle_type_villager_is_idle_villagers():
    s, b, me = script()
    n = sum(v.state == "idle" for v in b.g.villagers.values())
    assert s.check(("up-idle-unit-count", "idle-type-villager", "==", n))
    assert s.check(("up-idle-unit-count", "idle-villagers", "==", n))


def test_idle_type_id_is_the_name():
    s, b, me = script()
    n = sum(v.state == "idle" for v in b.g.villagers.values())
    assert s.check(("up-idle-unit-count", 0, "==", n))
    assert s.check(("up-idle-unit-count", 1, "==", 0))
