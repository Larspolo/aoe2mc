"""A warning line of a "Script Call" is printed once, not once for each pass of the trigger loop (#5792)."""
import numpy as np

import aoe2mc

XS = "int a = 1;\nvoid main() {\n  a = sin(a);\n}\n"


def trigger(id, enabled, effects):
    return dict(id=id, name=f"t{id}", enabled=enabled, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)


def test_each_xs_warning_prints_once_over_several_passes(capsys):
    script = dict(type=aoe2mc.XS_EFFECT, message=XS, player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)
    activate = dict(type=aoe2mc.ACTIVATE_TRIGGER, trigger=8, player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)
    chat = dict(type=aoe2mc.SEND_CHAT, message="Hi", player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)
    triggers = [trigger(7, True, [script, activate]), trigger(8, False, [chat])]
    aoe2mc.trigger_files(triggers, 4, np.full((64, 64), 70, np.int16))
    lines = [x for x in capsys.readouterr().out.splitlines() if "XS script" in x]
    assert len(lines) == len(set(lines))
    assert len(lines) >= 1
