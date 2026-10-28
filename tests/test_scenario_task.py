"""The trigger effect "Task Object" walks the units of a player in an area to a tile in the scenario mode (#2646): the
datapack tags them and writes the block into the storage aoe2mc:tasks, game/scenario.py walks them with aoe moveto."""
import numpy as np

import aoe2mc
from game import scenario


def effect(tile=(3, 5), area=(1, 2, 2, 3), player=1):
    return dict(type=aoe2mc.TASK_OBJECT, message="", player=player, time=0, object=None, tile=list(tile),
                area=list(area))


def lines(effects, T=4):
    trig = dict(id=7, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], T, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_task_object_tags_the_units_in_the_area_and_stores_the_block_of_the_tile():
    sel = f"@e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=4,y={aoe2mc.MIN_Y},z=8,dx=7,dy={aoe2mc.HEIGHT - 1},dz=7]"
    assert lines([dict(effect(), type=aoe2mc.SEND_CHAT, message="go"), effect()])[1:] == \
        [f"tag {sel} add aoe_task7_1",                                     # effect 1 of trigger 7
         "execute as @e[tag=aoe_task7_1] on vehicle run tag @s add aoe_task7_1",          # the horse of a rider,
         "execute as @e[tag=aoe_task7_1] on vehicle on passengers run tag @s remove aoe_task7_1",   # not the rider
         "data modify storage aoe2mc:tasks k7_1 set value [14.5d, 70.0d, 22.5d]"]


def test_no_area_or_tile_gives_no_line():
    for e in (effect(tile=(-1, -1)), effect(area=(-1, -1, -1, -1)), effect(tile=(40, 5))):
        assert lines([e]) == []


class Game:
    """A fake Gather: the answers of the server for the commands of scenario.tick."""

    def __init__(self, storage):
        self.storage, self.log = storage, []

    def clock(self):
        return 100.0

    def command(self, cmd):
        self.log.append(cmd)
        return f"Storage aoe2mc:tasks has the following contents: {self.storage}" if cmd.startswith("data get") else ""


def test_tick_walks_the_tagged_units_to_the_block_and_removes_the_task():
    g = Game("{k7_1: [14.5d, 70.0d, 22.5d], k9_0: [-3.5d, 64.0d, 2.5d]}")
    g.data, g.bots, g.who, g.player = {}, (), "@a[team=p1]", 1
    scenario.tick(g)
    assert [c for c in g.log if "task" in c] == [
        "data get storage aoe2mc:tasks",
        "aoe moveto @e[tag=aoe_task7_1] 14.5 70.0 22.5", "tag @e[tag=aoe_task7_1] remove aoe_task7_1",
        "data remove storage aoe2mc:tasks k7_1",
        "aoe moveto @e[tag=aoe_task9_0] -3.5 64.0 2.5", "tag @e[tag=aoe_task9_0] remove aoe_task9_0",
        "data remove storage aoe2mc:tasks k9_0"]


def test_no_task_sends_no_order():
    g = Game("{}")
    scenario.tasks(g)
    assert g.log == ["data get storage aoe2mc:tasks"]
