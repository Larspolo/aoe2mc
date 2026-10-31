"""game/per.py: an AI script tests what it can afford and build, and spies (#5044)."""
from test_bot_gather import bot_map

from game import per


def script(text, **stock):
    server, me, b = bot_map()
    b.g.stock.update(stock)
    return per.Script(per.parse(text), b), b


def fact(f, **stock):
    s, b = script(f"(defrule {f} => (set-goal 1 1))", **stock)
    s.step()
    return s.goals.get(1) == 1


def test_can_afford_tests_only_the_cost():
    full = dict(food=1000, wood=1000, gold=1000, stone=1000)
    for f in ("(can-afford-unit militiaman)", "(can-afford-building house)", "(can-afford-research ri-loom)"):
        assert fact(f, **full), f
    assert not fact("(can-afford-unit militiaman)", **full | {"food": 0})
    assert not fact("(can-afford-building house)", **full | {"wood": 0})
    assert not fact("(can-afford-research ri-loom)", **full | {"gold": 0})


def test_can_build_wall_needs_stone(monkeypatch):
    import build
    monkeypatch.setattr(build, "locked", lambda g, n: False)           # the Feudal Age
    assert fact("(can-build-wall 1 stone-wall-line)", stone=1000)
    assert not fact("(can-build-wall 1 stone-wall-line)", stone=0)
    assert fact("(can-afford-complete-wall 1 palisade-wall)", wood=5000)
    assert not fact("(can-afford-complete-wall 1 palisade-wall)", wood=10)


def test_spy_researches_spies_once():
    s, b = script("(defrule (can-spy) => (spy) (set-goal 2 1)) (defrule (can-spy) => (set-goal 3 1))", gold=5000)
    s.step()
    assert "SPIES" in b.g.techs and s.goals.get(2) == 1 and s.goals.get(3) is None
    left = b.g.stock["gold"]
    assert left < 5000
    s.step()
    assert b.g.stock["gold"] == left


def test_no_spy_without_gold_and_no_warning(capsys):
    s, b = script("(defrule (true) => (spy)) (defrule (can-build-gate 1) (can-spy-with-escrow) => (set-goal 1 1))", gold=0)
    s.step()
    assert "SPIES" not in b.g.techs and "unknown" not in capsys.readouterr().out
