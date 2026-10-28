"""#3077: a looping timer trigger that "Deactivate Trigger" names on itself fires once and stops, as in AoE2."""
import aoe2mc

FN = "data/aoe2mc/function/trigger/{}.mcfunction"


def trig(id, conds, effects, looping=False):
    return dict(id=id, name=f"t{id}", enabled=True, looping=looping,
                conditions=[dict(type=t, timer=s, inverted=False, quantity=1, player=1, area=[0, 0, 1, 1])
                            for t, s in conds],
                effects=[dict(type=t, message=m, player=1, time=-1, **({"trigger": k} if k is not None else {}))
                         for t, m, k in effects])


def test_a_looping_timer_that_deactivates_itself_only_reschedules_while_on():
    t = trig(3, [(aoe2mc.TIMER, 10)], [(aoe2mc.SEND_CHAT, "once", None), (aoe2mc.DEACTIVATE_TRIGGER, "", 3)],
             looping=True)
    _, files = aoe2mc.trigger_files([t])
    lines = files[FN.format(3)].splitlines()
    assert lines[-3:] == ["schedule clear aoe2mc:trigger/3", "scoreboard players set #3 aoe_on 0",
                          "execute if score #3 aoe_on matches 1 run schedule function aoe2mc:trigger/3 200t replace"]


def test_a_looping_timer_that_no_effect_names_keeps_the_plain_schedule():
    t = trig(3, [(aoe2mc.TIMER, 10)], [(aoe2mc.SEND_CHAT, "once", None)], looping=True)
    _, files = aoe2mc.trigger_files([t])
    assert files[FN.format(3)].splitlines()[-1] == "schedule function aoe2mc:trigger/3 200t replace"
