"""A trigger with "Clear Instructions" removes the shown instructions in the converted world (#2609)."""
import aoe2mc


def test_clear_instructions_comes_after_the_subtitle():
    t = dict(id=4, name="t4", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=10, inverted=False)],
             effects=[dict(type=aoe2mc.DISPLAY_INSTRUCTIONS, message="Go north.", player=1, time=4),
                      dict(type=aoe2mc.CLEAR_INSTRUCTIONS, message="", player=1, time=-1)])
    load, files = aoe2mc.trigger_files([t])
    lines = files["data/aoe2mc/function/trigger/4.mcfunction"].splitlines()
    assert lines[lines.index('title @a subtitle {"text": "Go north."}') + 2:] == ["title @a clear"]
