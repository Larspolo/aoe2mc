"""game/per.py: an error in one rule costs the rule only, not the game (#5823)."""
from test_per_afford import script


def test_failing_rule_is_skipped_with_one_warning(capsys, monkeypatch):
    s, b = script("(defrule (true) => (set-goal 2 1))\n(defrule (true) => (set-goal 1 1))")
    act = s.act
    monkeypatch.setattr(s, "act", lambda k, a: (_ for _ in ()).throw(TypeError("bad")) if k == 0 else act(k, a))
    s.step()
    s.step()
    assert s.goals.get(1) == 1 and 2 not in s.goals
    err = capsys.readouterr().err
    assert err.count("rule skipped") == 1 and ":1: error" in err


def test_modify_sn_with_text_value_does_nothing(capsys):
    s, b = script("(defrule (true) => (up-modify-sn sn-percent-civilian-explorers c:+ 1))\n(defrule (true) => (set-goal 1 1))")
    s.sn["sn-percent-civilian-explorers"] = "x"
    s.step()
    assert s.goals.get(1) == 1 and s.sn["sn-percent-civilian-explorers"] == "x"


def test_math_text_gives_none_and_one_warning(capsys):
    s, b = script("(defrule (true) => (set-goal 1 1))")
    assert s.math("+", "x", 1) is None and s.math("+", "x", 1) is None
    assert capsys.readouterr().err.count("unknown number") == 1
