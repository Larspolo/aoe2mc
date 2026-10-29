"""#3781 (epic #3774): an inverted condition "Victory Timer" holds while the timer is not in the range. The tick function
tests the score #p<player>.<type> of aoe_vic with `unless` when the condition is inverted."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import aoe2mc  # noqa: E402

LESS_OR_EQUAL = 3                                                      # AoE2 Comparison


def trig(inverted):
    c = dict(type=aoe2mc.VICTORY_TIMER, timer=0, inverted=inverted, quantity=50, player=2,
             comparison=LESS_OR_EQUAL, timer_type=0)
    return dict(id=3, name="t", enabled=True, looping=False, conditions=[c],
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Soon", player=1, time=0, object=None, tile=[-1, -1],
                              area=[-1] * 4)])


def tick(t):
    load, out = aoe2mc.trigger_files([t], 4, np.full((16, 16), 64, np.int16))
    return out.get("data/aoe2mc/function/tick.mcfunction", "")


def test_an_inverted_victory_timer_holds_while_the_timer_is_not_in_the_range():
    text = tick(trig(inverted=True))
    assert "unless score #p2.0 aoe_vic matches ..50 unless score #3 aoe_trig matches 1 run function aoe2mc:trigger/3" \
        in text
    assert "if score #p2.0 aoe_vic matches ..50" not in text


def test_a_victory_timer_that_is_not_inverted_keeps_if_score():
    text = tick(trig(inverted=False))
    assert "execute if score #p2.0 aoe_vic matches ..50 unless score #3 aoe_trig matches 1 run function " \
        "aoe2mc:trigger/3" in text
    assert "unless score #p2.0 aoe_vic" not in text
