"""#2754 (epic #2538): the trigger effect "Stop Object" stops the units of a player in an area. The converter tags the
units and puts the order "stop <tag>" into the data storage aoe2mc:orders; the scenario mode of the game program
stops them (`aoe stop`) and ends their trigger patrols."""
import os
import sys

import numpy as np

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402

STORED = "Storage aoe2mc:orders has the following contents: "


def trigger(area=(2, 2, 4, 4)):
    e = dict(type=aoe2mc.STOP_OBJECT, message="", player=1, time=0, object=None, tile=[-1, -1], area=list(area))
    return dict(id=8, name="Halt", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=[e])


def test_the_trigger_function_tags_the_units_and_stores_the_stop():
    _, files = aoe2mc.trigger_files([trigger()], 4, np.full((64, 64), 70, np.int16))
    lines = files["data/aoe2mc/function/trigger/8.mcfunction"].splitlines()
    at = "@e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=8,y=-64,z=8,dx=11,dy=383,dz=11]"
    assert lines[:4] == [f"tag {at} add aoe_order8_0", "execute as @e[tag=aoe_order8_0] on vehicle run tag @s add aoe_order8_0",
                         "execute as @e[tag=aoe_order8_0] on vehicle on passengers run tag @s remove aoe_order8_0",
                         'data modify storage aoe2mc:orders list append value "stop aoe_order8_0"']


def test_with_no_area_it_stops_the_units_of_the_player_on_the_whole_map():
    _, files = aoe2mc.trigger_files([trigger([-1] * 4)], 4, np.full((64, 64), 70, np.int16))
    assert files["data/aoe2mc/function/trigger/8.mcfunction"].startswith("tag @e[tag=aoe2mc.p1,tag=!aoe2mc.mount] add")


def play(*storage):
    """Run scenario.orders once for each storage text with a fake RCON. A patrol tag has units until a command removes
    it. Returns the game and the commands."""
    server, g, _ = game({"1": {}})
    command, log, gone = server.command, [], set()

    def answer(cmd):
        log.append(cmd)
        if cmd.startswith("data get storage aoe2mc:orders"):
            return stored
        if cmd.startswith("tag @e[tag=aoe_order8_0] remove "):
            gone.add(cmd.split()[-1])
        if cmd.startswith("execute positioned"):
            return "Test failed"
        if cmd.startswith("execute if entity @e[tag="):
            return "Test failed" if cmd.split("tag=")[1].split("]")[0] in gone else "Test passed, count: 2"
        return command(cmd)
    server.command = answer
    for stored in storage:
        scenario.orders(g)
    return g, log


def test_a_stop_ends_the_patrol_of_the_units():
    g, log = play(STORED + '["patrol aoe_order7_0 42 70 26 14 70 14"]', "Found no elements matching list",
                  STORED + '["stop aoe_order8_0"]', "Found no elements matching list")
    assert g.patrols == []
    stop = log.index("aoe stop @e[tag=aoe_order8_0]")
    assert "tag @e[tag=aoe_order8_0] remove aoe_order7_0" in log[:stop]
    assert "tag @e[tag=aoe_order8_0] remove aoe_order8_0" in log[stop:]
    assert not [c for c in log[stop:] if c.startswith("aoe moveto")]   # no next leg of the patrol


def test_a_stop_with_no_patrol_only_stops_the_units():
    g, log = play(STORED + '["stop aoe_order8_0"]')
    assert [c for c in log if c.startswith(("aoe ", "tag "))] == ["aoe stop @e[tag=aoe_order8_0]",
                                                                   "tag @e[tag=aoe_order8_0] remove aoe_order8_0"]
