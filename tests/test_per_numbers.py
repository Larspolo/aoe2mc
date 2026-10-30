"""game/per.py: an AI script sets and reads each AoE2 strategic number, also by its id (#4685)."""
from test_bot_gather import bot_map

from game import per


def script(monkeypatch, text):
    monkeypatch.setattr(per, "SN", {**per.SN, "sn-test-number": 5})      # test data
    monkeypatch.setattr(per, "SN_IDS", {77: "sn-test-number"})
    server, me, b = bot_map()
    b.script = per.Script(per.parse(text), b)
    b.step()
    return b.script


def test_a_number_without_effect_keeps_its_set_value(monkeypatch, capsys):
    s = script(monkeypatch, "(defrule (true) => (set-strategic-number sn-test-number 40) (disable-self))"
                            "(defrule (strategic-number sn-test-number == 40) => (set-goal 1 7))")
    assert s.goals == {1: 7} and capsys.readouterr().err == ""


def test_the_default_without_a_set(monkeypatch):
    assert script(monkeypatch, "(defrule (strategic-number sn-test-number == 5) => (set-goal 1 7))").goals == {1: 7}


def test_a_number_by_its_id(monkeypatch, capsys):
    s = script(monkeypatch, "(defrule (true) => (set-strategic-number 77 9) (disable-self))"
                            "(defrule (strategic-number 77 == 9) => (set-goal 1 7))")
    assert s.sn == {"sn-test-number": 9} and s.goals == {1: 7} and capsys.readouterr().err == ""


def test_an_unknown_name_warns_once(monkeypatch, capsys):
    script(monkeypatch, "(defrule (true) => (set-strategic-number sn-nothing 3))"
                        "(defrule (strategic-number sn-nothing == 3) => (set-goal 1 7))")
    assert capsys.readouterr().err.count("unknown strategic number sn-nothing") == 1

