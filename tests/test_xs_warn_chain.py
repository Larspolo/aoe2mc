"""Each XS warning line of a "Script Call" is printed once, also in a chain of triggers that all call it (#5809)."""
import numpy as np

import aoe2mc
from tests.test_xs_warn_once import XS, trigger


def effect(type, **kw):
    return dict(type=type, player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4, **kw)


def test_a_chain_of_triggers_prints_each_xs_warning_once(capsys):
    script = effect(aoe2mc.XS_EFFECT, message=XS)
    triggers = [trigger(i, i == 0, [script, effect(aoe2mc.ACTIVATE_TRIGGER, trigger=i + 1)]) for i in range(6)]
    triggers.append(trigger(6, False, [script, effect(aoe2mc.SEND_CHAT, message="Hi")]))
    aoe2mc.trigger_files(triggers, 4, np.full((64, 64), 70, np.int16))
    lines = [x for x in capsys.readouterr().out.splitlines() if "XS script" in x]
    assert lines and len(lines) == len(set(lines))
