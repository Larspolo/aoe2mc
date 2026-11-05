"""A defconst of a name again: the same value is accepted (AoE2 DE scenario AIs, #5797), another value is not."""
import pytest

from game import per


def test_same_value_again_is_accepted():
    consts = {}
    per.parse("(defconst a 1)\n(defconst a 1)", consts=consts)
    assert consts["a"] == 1


def test_other_value_again_raises():
    with pytest.raises(ValueError, match="defconst a again"):
        per.parse("(defconst a 1)\n(defconst a 2)")
