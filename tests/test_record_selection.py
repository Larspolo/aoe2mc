"""The selection of a command of a recorded game belongs to its player (#828): a command without own object IDs uses
the last selection of the same player, not that of another player (mgz keeps one selection for all players)."""
import os
from datetime import timedelta
from types import SimpleNamespace

import pytest

import aoe2mc

SAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")


def test_an_empty_selection_takes_the_last_one_of_the_same_player():
    from mgz.fast import Action
    from mgz.model.inputs import Inputs
    act = lambda n, ids: SimpleNamespace(timestamp=timedelta(0), type=Action.MOVE, player=SimpleNamespace(number=n),  # noqa: E731
                                         payload=dict(object_ids=ids, x=1.0, y=2.0), position=None)
    a, b, c, d = act(1, [10, 11]), act(2, [20]), act(1, []), act(2, [])
    add = Inputs.add_action
    with aoe2mc.own_selection():
        inputs = Inputs({})
        for x in (a, b, c, d):
            inputs.add_action(x)
        e = act(3, [])
        inputs.add_action(e)
    assert c.payload["object_ids"] == [10, 11] and d.payload["object_ids"] == [20] and e.payload["object_ids"] == []
    assert Inputs.add_action is add                              # the patch ends with the block


@pytest.mark.parametrize("name", ["de-64.3.aoe2record", "hd-4.6.aoe2record"])
def test_no_command_selects_a_start_unit_of_another_player(name):
    path = os.path.join(SAMPLES, name)
    timeline = aoe2mc.read_timeline(path)
    if timeline is None:                                         # the mgz model cannot read it (HD, #376)
        return
    owner = {o["ref"]: o["player"] for o in aoe2mc.read_record(path)[5]}
    wrong = [(e["time"], e["player"], i) for e in timeline if e["kind"] in ("move", "order")
             for i in e.get("objects", []) if owner.get(i, 0) not in (0, e["player"])]
    assert wrong == [], wrong[:10]
