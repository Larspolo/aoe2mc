""""Own Objects" and "Own Fewer Objects" count the units of the whole map, also in chunks with no player: the load
function forceloads the map and the tick lines wait for the score #loaded of aoe_trig (#3080)."""
import json
import os
import time

import numpy as np
import pytest

import aoe2mc
from tools import scenarios

TICK = "data/aoe2mc/function/tick.mcfunction"
LOADED = "data/aoe2mc/function/loaded.mcfunction"


def own(id, kind, player, quantity, variable, area=(-1, -1, -1, -1)):
    return dict(id=id, name=f"t{id}", enabled=True, looping=False,
                conditions=[dict(type=kind, timer=-1, inverted=False, quantity=quantity, player=player,
                                 area=list(area), object=-1, group=-1, **{"class": -1})],
                effects=[dict(type=aoe2mc.CHANGE_VARIABLE, message="", player=-1, time=0, variable=variable,
                              operation=1, quantity=1)])


def test_own_objects_forceload_the_map_and_wait_for_it():
    ground = np.zeros((480, 300), np.int16)                            # 30 × 19 chunks: two boxes in x, two in z
    load, files = aoe2mc.trigger_files([own(0, aoe2mc.OWN_FEWER_OBJECTS, 2, 0, 1),
                                        own(1, aoe2mc.OWN_OBJECTS, 2, 1, 2)], T=4, ground=ground)
    boxes = [x for x in load if x.startswith("forceload add ")]
    assert boxes == ["forceload add 0 0 240 240", "forceload add 0 256 240 288",
                     "forceload add 256 0 464 240", "forceload add 256 256 464 288"]
    for b in boxes:                                                    # at most 16 × 16 chunks per command
        x0, z0, x1, z1 = map(int, b.split()[2:])
        assert (x1 - x0) // 16 + 1 <= 16 and (z1 - z0) // 16 + 1 <= 16
    assert "scoreboard players set #loaded aoe_trig 0" in load
    assert "schedule function aoe2mc:loaded 20t replace" in load
    lines = files[LOADED].splitlines()
    assert lines[0] == "scoreboard players set #loaded aoe_trig 1"
    assert "execute unless loaded 464 0 288 run scoreboard players set #loaded aoe_trig 0" in lines
    assert len(lines) == 2 + 30 * 19
    tick = files[TICK].splitlines()
    assert tick[1] == ("execute if score #loaded aoe_trig matches 1 if score #0.0 aoe_trig matches ..0 "
                       "unless score #0 aoe_trig matches 1 run function aoe2mc:trigger/0")
    assert tick[2] == ("execute if score #loaded aoe_trig matches 1 if entity @e[tag=aoe2mc.p2,tag=!aoe2mc.mount] "
                       "unless score #1 aoe_trig matches 1 run function aoe2mc:trigger/1")


def test_objects_in_area_forceloads_only_its_area():
    t = own(2, aoe2mc.IN_AREA, 1, 1, 1, area=(10, 2, 5, 3))
    load, files = aoe2mc.trigger_files([t], T=4, ground=np.zeros((480, 480), np.int16))
    assert [x for x in load if "forceload" in x] == ["forceload add 16 0 32 0"]   # blocks 20..43, 8..15
    assert LOADED not in files and "#loaded" not in files[TICK]


def test_no_count_condition_no_forceload():
    timer = dict(own(3, aoe2mc.TIMER, -1, 0, 1), conditions=[dict(type=aoe2mc.TIMER, timer=5, inverted=False)])
    load, files = aoe2mc.trigger_files([timer], T=4, ground=np.zeros((480, 480), np.int16))
    assert not any("forceload" in x for x in load) and LOADED not in files


def variable(game, n):
    out = game.command(f"scoreboard players get #v{n} aoe_var")
    return int(out.split(" has ")[1].split()[0]) if " has " in out else None


@pytest.mark.mc
def test_own_fewer_objects_waits_for_far_units_on_a_server(tmp_path):
    from test_paper import paper_reachable
    from game import run
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = str(tmp_path / "W")
    src = scenarios.battle(str(tmp_path / "b.aoe2scenario"))
    aoe2mc.convert(src, world)
    size = aoe2mc.read_scenario(src)[0] * 4
    load, files = aoe2mc.trigger_files([own(0, aoe2mc.OWN_FEWER_OBJECTS, 2, 0, 1), own(1, aoe2mc.OWN_OBJECTS, 2, 1, 2)],
                                       T=4, ground=np.zeros((size, size), np.int16))
    pack = os.path.join(world, "datapacks", "aoe2mc")
    files["data/aoe2mc/function/load.mcfunction"] = "\n".join(load) + "\n"
    for name, text in files.items():
        os.makedirs(os.path.dirname(os.path.join(pack, name)), exist_ok=True)
        with open(os.path.join(pack, name), "w") as f:
            f.write(text if isinstance(text, str) else json.dumps(text))
    with run.Game(world) as game:                                      # no player, no game.forceload()
        end = time.time() + 10
        while time.time() < end:
            assert variable(game, 1) in (0, None)                      # player 2 has units: "Own Fewer Objects" waits
            time.sleep(0.5)
        assert variable(game, 2) == 1                                  # "Own Objects" fires
        assert variable(game, 1) == 0
