"""The guard flag names of up-compare-flag (airef pGuardFlag, #5093): a name gives its bit; an unknown name warns."""
from test_per_bot import scripted


def test_guard_flag_names_test_the_bits_of_the_goal():
    b = scripted("(defrule (true) => (disable-self))")
    b.script.goals[103] = 6
    s = b.script
    assert s.check(("up-compare-flag", 103, "==", "guard-flag-resource"))
    assert not s.check(("up-compare-flag", 103, "==", "guard-flag-victory"))
    assert s.check(("up-compare-flag", 103, "!=", "guard-flag-victory"))


def test_unknown_guard_flag_warns_once_and_is_false(capsys):
    b = scripted("(defrule (true) => (disable-self))")
    b.script.goals[103] = 6
    assert not b.script.check(("up-compare-flag", 103, "==", "guard-flag-unknown"))
    assert not b.script.check(("up-compare-flag", 103, "==", "guard-flag-unknown"))
    assert capsys.readouterr().err.count("unknown guard flag guard-flag-unknown") == 1
