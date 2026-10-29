"""The code of technology effects, with test data: a factor of a float field, the test "foot_archers" and the key
"regen", the key "pack_time", the "walk" lists and buildings and the key "more_arrows" (#4098, #4150, #4255, #4275,
#4254, #4258). These replace tests of single data lines (owner,
2026-10-29, #4242)."""
from test_train_castle import setup

import pytest
import train as plain_train          # civs.regen and trebuchet.pack_time import train by its plain name (not game.train)
from game import civs, combat, garrison, train, trebuchet


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


def test_a_researched_technology_changes_the_pack_time_of_trebuchets(monkeypatch):
    tech = next(t for t in train.TECHS if t not in plain_train.BY_KEY["pack_time"])   # train.stats needs a real name
    monkeypatch.setitem(plain_train.BY_KEY["pack_time"], tech, 0.5)
    server, g = setup("BRITONS", ages=3)
    assert trebuchet.pack_time(g) == pytest.approx(trebuchet.PACK)
    g.techs.add(tech)
    assert trebuchet.pack_time(g) == pytest.approx(trebuchet.PACK * 0.5)
    g.soldiers["t"] = "TREBUCHET"
    trebuchet.tick(g, 0.0)
    g.choose({"t"}, "t")
    g.attack("fort")                                                  # no position: in range (#1400)
    assert trebuchet.state(g, "t") == "unpacking" and g.trebs["t"][1] == pytest.approx(trebuchet.PACK * 0.5)


def test_a_walk_entry_takes_a_list_and_a_building():
    workshop = next(b for n, b in train.BUILDING_OF.items() if n == "BATTERING_RAM")
    trained = [n for n, b in train.BUILDING_OF.items() if b == workshop and n in combat.STATS]
    other = next(n for n, b in train.BUILDING_OF.items() if b and b != workshop and n in combat.STATS)
    assert trained and all(train.faster(workshop, n) for n in trained)
    assert not train.faster(workshop, other)
    assert train.faster(["NO_SUCH_UNIT", other], other) and not train.faster(["NO_SUCH_UNIT"], other)


def test_a_researched_technology_adds_arrows_to_its_buildings(monkeypatch):
    tech = next(t for t in train.TECHS if t not in train.BY_KEY["more_arrows"])         # train.stats needs a real name
    for m in (train, plain_train):                                  # garrison imports train by its plain name
        monkeypatch.setitem(m.BY_KEY["more_arrows"], tech, {"TOWN_CENTER": 3})
    server, g = setup("BRITONS")
    rect = next(r for r, o in garrison.holders(g).items() if o["name"] == "TOWN_CENTER")
    count = lambda: int(garrison.arrows_command(g, rect).split()[-1])            # noqa: E731
    before = count()
    sent, command = [], g.command
    g.command = lambda c: (sent.append(c), command(c))[1]
    train.research(g, {"name": tech, "player": "Steve"})              # a queue entry
    assert count() == before + 3 and garrison.arrows_command(g, rect) in sent
    assert train.more_arrows(g, "WATCH_TOWER") == 0
