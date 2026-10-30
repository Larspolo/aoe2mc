"""A trigger with no conditions fires as soon as it is on, as in AoE2 (#2972)."""
from test_trigger_activate import FN, trig

import aoe2mc


def test_a_trigger_with_no_conditions_fires_at_the_start_and_after_an_activation():
    start = trig(5, [], [(aoe2mc.SEND_CHAT, "Start", None)])
    timer = trig(6, [(aoe2mc.TIMER, 5)], [(aoe2mc.ACTIVATE_TRIGGER, "", 7)])
    later = trig(7, [], [(aoe2mc.SEND_CHAT, "Activated", None)], enabled=False)
    load, files = aoe2mc.trigger_files([start, timer, later])
    assert "schedule function aoe2mc:trigger/5 1t replace" in load
    assert "schedule function aoe2mc:trigger/6 100t replace" in load
    assert not [x for x in load if "trigger/7" in x]                   # disabled: only the activation starts it
    assert "execute unless score #7 aoe_on matches 1 run schedule function aoe2mc:trigger/7 1t replace" \
        in files[FN.format(6)].splitlines()
    assert files[FN.format(5)].splitlines() == ['tellraw @a {"text": "Start"}']
    assert files[FN.format(7)].splitlines() == ['tellraw @a {"text": "Activated"}', "scoreboard players set #7 aoe_on 0"]


def test_a_looping_trigger_with_no_conditions_fires_once_per_second_until_deactivated():
    loop = trig(1, [], [(aoe2mc.SEND_CHAT, "Again", None)], looping=True)
    stop = trig(2, [(aoe2mc.TIMER, 9)], [(aoe2mc.DEACTIVATE_TRIGGER, "", 1)])
    load, files = aoe2mc.trigger_files([loop, stop])
    assert "schedule function aoe2mc:trigger/1 1t replace" in load
    assert files[FN.format(1)].splitlines() == ['tellraw @a {"text": "Again"}',
                                                "schedule function aoe2mc:trigger/1 20t replace"]
    assert files[FN.format(2)].splitlines()[0] == "schedule clear aoe2mc:trigger/1"


def test_a_trigger_with_no_conditions_and_no_command_gets_no_function():
    load, files = aoe2mc.trigger_files([trig(3, [], [])])
    assert FN.format(3) not in files and not [x for x in load if "trigger/3" in x]
