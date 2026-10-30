"""#2647 (epic #2538): the trigger effects "Patrol" and "Attack Move" give their orders to the units of a player in an
area. The converter tags the units and puts the order into the data storage aoe2mc:orders; the scenario mode of the
game program reads it with RCON and walks the units with the Paper plugin."""
import os
import sys

import numpy as np

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import savegame  # noqa: E402
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402


def trigger(*kinds):
    effects = [dict(type=k, message="", player=1, time=0, object=None, tile=[10, 6], area=[2, 2, 4, 4]) for k in kinds]
    return dict(id=7, name="Go", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)


def test_the_trigger_function_tags_the_units_and_stores_the_orders():
    _, files = aoe2mc.trigger_files([trigger(aoe2mc.PATROL, aoe2mc.ATTACK_MOVE)], 4, np.full((64, 64), 70, np.int16))
    lines = files["data/aoe2mc/function/trigger/7.mcfunction"].splitlines()
    area = "x=8,y=-64,z=8,dx=11,dy=383,dz=11"
    at = f"@e[tag=aoe2mc.p1,tag=!aoe2mc.mount,{area}]"
    assert lines[:4] == [f"tag {at} add aoe_order7_0", "execute as @e[tag=aoe_order7_0] on vehicle run tag @s add aoe_order7_0",
                         "execute as @e[tag=aoe_order7_0] on vehicle on passengers run tag @s remove aoe_order7_0",
                         'data modify storage aoe2mc:orders list append value "patrol aoe_order7_0 42 70 26 14 70 14"']
    assert lines[4].endswith(" add aoe_order7_1")                       # a rider walks on its horse
    assert lines[7] == 'data modify storage aoe2mc:orders list append value "attack_move aoe_order7_1 42 70 26"'


def test_an_order_with_no_area_or_tile_has_no_lines():
    t = trigger(aoe2mc.PATROL)
    t["effects"][0]["tile"] = [-1, -1]
    assert aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1] == {}


def play(orders, near=(), alive=True):
    """Run scenario.tick twice with a fake RCON: the storage holds the orders, the units of the tags in near are at
    their patrol point at the second tick; alive: the tagged units live."""
    server, g, _ = game({"1": {}})
    command, stored = server.command, [orders]

    def answer(cmd):
        if cmd.startswith("data remove storage aoe2mc:orders"):
            stored[0] = "Found no elements matching list"
        if cmd.startswith(("data get storage aoe2mc:orders", "execute positioned", "execute if entity @e[tag=aoe_o")):
            server.log.append(cmd)
        if cmd.startswith("data get storage aoe2mc:orders"):
            return stored[0]
        if cmd.startswith("execute positioned"):
            return "Test passed, count: 1" if g.clock() > 0 and any(f"tag={t}," in cmd for t in near) else "Test failed"
        if cmd.startswith("execute if entity @e[tag=aoe_order"):
            return "Test passed, count: 2" if alive else "Test failed"
        return command(cmd)
    server.command = answer
    for t in (0.0, 2.0):
        g.clock = lambda t=t: t
        scenario.tick(g)
    return g, server.log


def test_an_attack_move_walks_the_tagged_units_with_the_aggressive_stance():
    g, log = play('Storage aoe2mc:orders has the following contents: ["attack_move aoe_order7_1 42 70 26"]')
    assert log.index("aoe stance @e[tag=aoe_order7_1] aggressive") < log.index("aoe moveto @e[tag=aoe_order7_1] 42 70 26")
    assert "tag @e[tag=aoe_order7_1] remove aoe_order7_1" in log
    assert log.count("data remove storage aoe2mc:orders list") == 1 and g.patrols == []


def test_a_patrol_walks_to_the_tile_and_back():
    g, log = play('Storage aoe2mc:orders has the following contents: ["patrol aoe_order7_0 42 70 26 14 70 14"]',
                  near={"aoe_order7_0"})
    walks = [c for c in log if c.startswith("aoe moveto")]
    assert walks == ["aoe moveto @e[tag=aoe_order7_0] 42 70 26", "aoe moveto @e[tag=aoe_order7_0] 14 70 14"]
    assert g.patrols == [["aoe_order7_0", [[42, 70, 26], [14, 70, 14]], 1]]
    assert "patrols" in savegame.KEPT                                  # a saved game keeps the patrol


def test_a_patrol_waits_for_its_units_and_ends_with_no_unit():
    order = 'Storage aoe2mc:orders has the following contents: ["patrol aoe_order7_0 42 70 26 14 70 14"]'
    assert play(order)[0].patrols == [["aoe_order7_0", [[42, 70, 26], [14, 70, 14]], 0]]   # on the way
    assert play(order, alive=False)[0].patrols == []
