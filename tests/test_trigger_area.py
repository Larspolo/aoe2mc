"""Triggers with the condition "Objects in Area" fire when units of their player enter the area (#649)."""
import os

import pytest

import aoe2mc
from tools import scenarios

TICK = "data/aoe2mc/function/tick.mcfunction"


def area(id, areas, effects=((aoe2mc.SEND_CHAT, "In the area."),), looping=False, enabled=True):
    return dict(id=id, name=f"t{id}", enabled=enabled, looping=looping,
                conditions=[dict(type=aoe2mc.IN_AREA, timer=-1, inverted=False, quantity=q, player=p, area=a)
                            for p, q, a in areas],
                effects=[dict(type=t, message=m, player=1, time=-1) for t, m in effects])


def test_scenario_area_trigger_gives_a_tick_line(tmp_path):
    texts = aoe2mc.read_scenario(scenarios.triggers(str(tmp_path / "t.aoe2scenario")))[4]
    knight = texts["triggers"][1]["conditions"][0]
    assert (knight["quantity"], knight["player"], knight["area"]) == (1, 1, [3, 3, 6, 6])
    load, files = aoe2mc.trigger_files(texts["triggers"], T=4)
    assert load[0] == "scoreboard objectives add aoe_trig dummy"
    assert files["data/minecraft/tags/function/tick.json"] == {"values": ["aoe2mc:tick_wait"]}
    # tiles 3..6 are the blocks 12..27: dx 15; all heights
    assert files[TICK].splitlines() == [
        "execute if entity @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,tag=aoe2mc.t38,x=12,y=-64,z=12,dx=15,dy=383,dz=15] unless score #1 aoe_trig matches 1 "
        "run function aoe2mc:trigger/1"]
    assert files["data/aoe2mc/function/trigger/1.mcfunction"].splitlines() == [
        'data modify storage aoe2mc:orders list append value "create 1 MONASTERY 8 4"',   # #2911
        'tellraw @a {"text": "A monastery stands now next to the hill."}', "scoreboard players set #1 aoe_trig 1"]


def test_trigger_that_does_not_loop_fires_once():
    _, files = aoe2mc.trigger_files([area(2, [(2, 1, [0, 1, 0, 1])])], T=2)
    assert files[TICK] == ("execute if entity @e[tag=aoe2mc.p2,tag=!aoe2mc.mount,x=0,y=-64,z=2,dx=1,dy=383,dz=1] "
                           "unless score #2 aoe_trig matches 1 run function aoe2mc:trigger/2\n")
    assert "scoreboard players set #2 aoe_trig 1" in files["data/aoe2mc/function/trigger/2.mcfunction"]


def test_looping_trigger_fires_again_after_the_units_leave():
    _, files = aoe2mc.trigger_files([area(3, [(1, 1, [5, 5, 4, 4])], looping=True)], T=4)
    sel = "@e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=16,y=-64,z=16,dx=7,dy=383,dz=7]"        # corners in any order
    assert files[TICK].splitlines()[1] == f"execute unless entity {sel} run scoreboard players reset #3 aoe_trig"


def test_quantity_and_whole_map():
    _, files = aoe2mc.trigger_files([area(4, [(1, 3, [-1, -1, -1, -1]), (2, 1, [0, 0, 1, 1])])], T=4)
    lines = files[TICK].splitlines()
    assert lines[0] == "execute store result score #4.0 aoe_trig if entity @e[tag=aoe2mc.p1,tag=!aoe2mc.mount]"
    assert lines[1].startswith("execute if score #4.0 aoe_trig matches 3.. if entity @e[tag=aoe2mc.p2,tag=!aoe2mc.mount,x=0,")


def test_mixed_inverted_or_silent_triggers_give_no_tick():
    triggers = [area(5, [(1, 1, [0, 0, 1, 1])], effects=((11, ""),)),              # no chat effect
                area(6, [(1, 1, [0, 0, 1, 1])], enabled=False)]
    inverted = area(8, [(1, 1, [0, 0, 1, 1])])
    inverted["conditions"][0]["inverted"] = True
    assert aoe2mc.trigger_files(triggers + [inverted]) == ([], {})   # a timer AND an area: #3891


def test_area_turns_with_the_map():
    assert aoe2mc.turn_area([3, 3, 6, 6], 24, 0) == [3, 3, 6, 6]
    assert aoe2mc.turn_area([0, 1, 2, 5], 24, 1) == [18, 0, 22, 2]       # tile (x, y) -> (size - 1 - y, x)
    assert aoe2mc.turn_area([-1, -1, -1, -1], 24, 1) == [-1, -1, -1, -1]


def score(game):
    out = game.command("scoreboard players get #1 aoe_trig")
    return int(out.split(" has ")[1].split()[0]) if " has " in out else None


def wait_score(game, want, secs=5):
    import time
    end = time.time() + secs
    while time.time() < end and score(game) != want:
        time.sleep(0.2)
    return score(game)


@pytest.mark.mc
def test_area_trigger_fires_on_a_server(tmp_path):
    from test_paper import paper_reachable
    from game import run
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    src = scenarios.triggers(str(tmp_path / "t.aoe2scenario"))
    world = str(tmp_path / "W")
    aoe2mc.convert(src, world)
    fn = os.path.join(world, "datapacks", "aoe2mc", "data", "aoe2mc", "function")
    unit = "@e[tag=aoe2mc.p1,type=villager,limit=1]"
    texts = aoe2mc.read_scenario(src)[4]
    texts["triggers"][1]["conditions"][0]["object"] = -1             # any unit, not only the knight (#681)
    with open(os.path.join(fn, "tick.mcfunction"), "w") as f:
        f.write(aoe2mc.trigger_files(texts["triggers"], T=4)[1]["data/aoe2mc/function/tick.mcfunction"])
    with run.Game(world) as game:
        game.forceload()
        assert wait_score(game, None, 2) is None                      # the villager is outside the area
        game.command(f"tp {unit} 20 70 20")
        assert wait_score(game, 1) == 1                               # in the area: the trigger fired
        game.command(f"tp {unit} 60 70 60")
        assert wait_score(game, None, 2) == 1                         # no loop: it stays fired
        texts["triggers"][1]["looping"] = True
        files = aoe2mc.trigger_files(texts["triggers"], T=4)[1]
        with open(os.path.join(fn, "tick.mcfunction"), "w") as f:
            f.write(files["data/aoe2mc/function/tick.mcfunction"])
        game.command("reload")
        assert wait_score(game, None) is None                          # looping: outside resets it
        game.command(f"tp {unit} 20 70 20")
        assert wait_score(game, 1) == 1                               # and it fires again
