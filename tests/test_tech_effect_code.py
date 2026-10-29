"""The code of technology effects, with test data: a factor of a float field, the test "foot_archers" and the key
"regen" (#4098, #4150, #4255). These replace tests of single data lines (owner, 2026-10-29, #4242)."""
from test_train_castle import setup

import train as plain_train                       # civs.regen imports train by its plain name (not game.train)
from game import civs, combat, train


def test_a_factor_keeps_a_float_field_a_float_and_rounds_an_int_field():
    s = combat.stats("KNIGHT")._replace(reload=2.0, hp=100)
    t = train.effect({"times": {"reload": 0.75, "hp": 1.333}})("KNIGHT", s)
    assert t.reload == 1.5 and t.hp == 133 and isinstance(t.hp, int)


def test_the_test_foot_archers_is_the_civ_rule():
    for name, s in combat.STATS.items():
        assert train.test({"test": "foot_archers"}, name, s) == civs.foot_archer(s), name


def test_a_researched_technology_adds_its_regeneration_to_its_group(monkeypatch):
    monkeypatch.setitem(civs.GROUPS, "TEST_GROUP", lambda n, s: n == "KNIGHT")
    monkeypatch.setitem(plain_train.BY_KEY["regen"], "TEST_TECH", ("TEST_GROUP", 7))
    server, g = setup("BRITONS")
    knight, militia = (civs.regen(g, n, combat.stats(n)) for n in ("KNIGHT", "MILITIA"))
    g.techs.add("TEST_TECH")
    assert civs.regen(g, "KNIGHT", combat.stats("KNIGHT")) == knight + 7
    assert civs.regen(g, "MILITIA", combat.stats("MILITIA")) == militia      # not in the group
