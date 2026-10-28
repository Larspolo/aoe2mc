"""A trigger effect is one line in aoe2mc.EFFECTS and its handler (#2613): trigger_files runs the handler of each
effect with the context of its trigger, and an effect with no handler gives no command."""
import re

import aoe2mc
from test_trigger_objects import effect, lines


def test_trigger_files_runs_the_handler_of_each_effect_in_order(monkeypatch):
    seen = []
    monkeypatch.setitem(aoe2mc.EFFECTS, 99, lambda e, c: seen.append((c.t["id"], c.T, c.mood)) or [f"say {e['player']}"])
    assert lines([effect(99, player=2), effect(aoe2mc.SEND_CHAT), effect(99, player=3)]) == ["say 2", "say 3"]
    assert seen == [(7, 4, True)] * 2                                  # a chat with no message gives no command


def test_an_effect_with_no_handler_gives_no_command():
    assert 1000 not in aoe2mc.EFFECTS and lines([effect(1000)]) == []     # 99 is "Enable Unit Attackable" (#2695)


def test_the_effects_are_in_alphabetical_order():
    """Parallel tickets add their lines in order, not at the end: fewer merge conflicts."""
    src = open(aoe2mc.__file__).read()
    order = re.findall(r"^    ([A-Z_]+): \w+,$", src[src.index("\nEFFECTS = {"):], re.M)[:len(aoe2mc.EFFECTS)]
    assert order == sorted(order) and {getattr(aoe2mc, n) for n in order} == set(aoe2mc.EFFECTS)
