"""A defconst with a name or a text value stands for that value where the script uses it (#5098)."""
import pytest

from game import per


def test_name_and_text_values():
    (named,) = per.parse("(defconst scout-unit scout-cavalry)\n(defrule (unit-type-count scout-unit == 0) => (do-nothing))")
    (plain,) = per.parse("(defrule (unit-type-count scout-cavalry == 0) => (do-nothing))")
    assert named.facts == plain.facts
    (rule,) = per.parse('(defconst t1 "one")\n(defrule (true) => (chat-to-all t1))')
    assert rule.actions == (("chat-to-all", "one"),) and isinstance(rule.actions[0][1], per.Text)


@pytest.mark.parametrize("text", ["(defconst x (true))", "(defconst x 32768)", "(defconst x -32769)"])
def test_bad_values(text):
    with pytest.raises(ValueError, match="defconst must be"):
        per.parse(text)
