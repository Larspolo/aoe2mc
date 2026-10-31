"""game/per.py: the airef names that need code (#5183): two player terms (any-human-ally), the post-imperial starting
age, and a class in up-drop-resources (farm-class: the farmers)."""
import diplomacy  # per imports it by its plain name
from test_per_players import script
from test_per_up_workers import scripted, working

from game import per


def test_any_human_ally_needs_both_terms(capsys, monkeypatch):
    s, b, me = script()
    me.pop = 7
    assert not s.check(("players-population", "any-human-ally", ">=", 0))      # the person is an enemy
    monkeypatch.setattr(diplomacy, "stance", lambda g, n: "ally")
    assert s.check(("players-population", "any-human-ally", "==", 7))
    assert not s.check(("players-population", "any-computer-ally", ">=", 0))   # the person is no computer
    assert s.check(("players-population", "every-human-ally", "==", 7))
    assert "unknown" not in capsys.readouterr().err
    assert not s.check(("players-population", "any-human-ally-enemy", ">=", 0))   # three terms: a warning
    assert "unknown" in capsys.readouterr().err


def test_post_imperial_is_an_age(capsys):
    s, b, me = script()
    assert s.age_of("post-imperial") == s.age_of("post-imperial-age")
    assert s.check(("starting-age", "<", "post-imperial"))
    assert "unknown" not in capsys.readouterr().err


def test_up_drop_resources_of_a_class_sends_only_its_villagers():
    b = scripted("(defrule (true) => (up-drop-resources farm-class c: 5) (disable-self))")
    working(b, "food", 4)
    us = sorted(b.g.villagers)[:4]
    for u, task in zip(us, ("FARMER", "FARMER", "FORAGER", "FARMER")):
        b.g.villagers[u].task, b.g.villagers[u].load = task, 10
    b.g.villagers[us[3]].load = 2
    b.script.step()
    assert {u for u, v in b.g.villagers.items() if v.state == "to_drop"} == set(us[:2])
    assert not b.script.warned
    assert per.DROP_CLASSES["farm-class"][0] in per.STOCK
