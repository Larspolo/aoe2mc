"""#3074: the start state of the triggers runs at the first load of a world only, not at each server start."""
import contextlib
import io
import os
import shutil

import numpy as np
import pytest

import aoe2mc


def trig(id, conds, effects):
    return dict(id=id, name=f"t{id}", enabled=True, looping=False,
                conditions=[dict(type=t, timer=s, inverted=False, quantity=1, player=1, area=[0, 0, 1, 1])
                            for t, s in conds],
                effects=[dict(type=t, message=m, player=1, time=-1, **({"trigger": k} if k is not None else {}))
                         for t, m, k in effects])


def read(root, name):
    with open(os.path.join(root, "datapacks", "aoe2mc", "data", "aoe2mc", "function", name)) as f:
        return f.read()


def test_the_start_state_runs_once(tmp_path):
    triggers = [trig(0, [(aoe2mc.TIMER, 5)], [(aoe2mc.SEND_CHAT, "Welcome", None)]),
                trig(1, [(aoe2mc.IN_AREA, 0)], [(aoe2mc.DEACTIVATE_TRIGGER, "", 2)]),
                trig(2, [(aoe2mc.TIMER, 60)], [(aoe2mc.SEND_CHAT, "Archer leaves", None)]),
                trig(3, [(aoe2mc.TIMER, 20)], [(aoe2mc.SEND_CHAT, "Militia", None)])]
    aoe2mc.write_datapack(str(tmp_path), [], np.zeros((4, 4), np.int16), players={1: {"color": 1}},
                          triggers=triggers)
    load, start = read(tmp_path, "load.mcfunction"), read(tmp_path, "start.mcfunction").splitlines()
    assert "schedule function aoe2mc:trigger/" not in load and "players set #2 aoe_on" not in load and " color " not in load
    assert "execute unless score #start aoe_trig matches 1 run function aoe2mc:start" in load.splitlines()
    for line in ("schedule function aoe2mc:trigger/0 100t replace", "scoreboard players set #2 aoe_on 1",
                 "schedule function aoe2mc:trigger/2 1200t replace", "schedule function aoe2mc:trigger/3 400t replace"):
        assert line in start
    assert any(x.startswith("team modify p1 color ") for x in start)
    assert start[-1] == "scoreboard players set #start aoe_trig 1"


@pytest.mark.mc
def test_a_second_server_start_does_not_fire_a_timer_again(tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    from test_triggers_server import MILITIA, count, scenario, wait
    if not mojang_reachable() or not paper_reachable() or not shutil.which("java"):
        pytest.skip("Mojang, Paper or Java is not available")
    from game import run
    src = scenario(str(tmp_path / "t.aoe2scenario"))
    world = str(tmp_path / "W")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, world)
    with run.Game(world) as game:
        game.forceload()
        assert wait(lambda: count(game, MILITIA) == 1, 30)                 # "Militia comes" at 10 s
    with run.Game(world) as game:
        game.forceload()
        assert not wait(lambda: count(game, MILITIA) > 1, 20) and count(game, MILITIA) == 1
