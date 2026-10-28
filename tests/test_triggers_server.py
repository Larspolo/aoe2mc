"""The triggers scenario on a real server (#676): no datapack errors, and the effects happen at their time."""
import contextlib
import io
import os
import re
import shutil
import time

import pytest

import aoe2mc
import mc_check
import mc_shot
from test_mc_check import mojang_reachable
from tools import scenarios

WELCOME = "[CHAT] Welcome to the tiny map."
MILITIA = "@e[type=minecraft:zombie,tag=aoe2mc.p1,x=64,y=-64,z=64,dx=3,dy=383,dz=3]"    # tile (16, 16)
ARCHERS = "@e[type=minecraft:skeleton,tag=aoe2mc.p2]"


def scenario(path):
    """The triggers scenario and one more timer trigger: a militia comes at 10 s (Create Object of a unit)."""
    from AoE2ScenarioParser.datasets.units import UnitInfo
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.triggers(path + ".base"))
    t = scn.trigger_manager.add_trigger("Militia comes")
    t.new_condition.timer(timer=10)
    t.new_effect.create_object(source_player=1, object_list_unit_id=UnitInfo.MILITIA.ID, location_x=16, location_y=16)
    return scenarios.save(scn, path)


def count(game, sel):
    out = game.command(f"execute if entity {sel}")
    m = re.search(r"count: (\d+)", out, re.I)
    return int(m.group(1)) if m else 0


def wait(cond, secs):
    end = time.time() + secs
    while not cond() and time.time() < end:
        time.sleep(0.5)
    return cond()


def datapack_problems(log):
    return [p for p in mc_check.problems(log) if re.search(r"function|data ?pack|aoe2mc:", p, re.I)]


def test_the_scenario_has_the_militia_trigger(tmp_path):
    src = scenario(str(tmp_path / "t.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    fn = os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function")
    with open(os.path.join(fn, "trigger", "3.mcfunction")) as f:
        assert f.read().startswith("summon minecraft:zombie 66.5 ")         # the middle of tile (16, 16)
    with open(os.path.join(fn, "start.mcfunction")) as f:
        assert "schedule function aoe2mc:trigger/3 200t replace" in f.read()


@pytest.mark.mc
def test_the_triggers_run_on_a_server(tmp_path):
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    from game import run
    src = scenario(str(tmp_path / "t.aoe2scenario"))
    world = str(tmp_path / "W")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, world)
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        game.command("tick freeze")                                    # the timers wait until the client is there
        game.forceload()
        assert wait(lambda: count(game, ARCHERS) > 0, 20)
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        militia = count(game, MILITIA)
        game.command("tick unfreeze")
        t0 = time.time()
        assert wait(lambda: WELCOME in client.text(), 20), client.text()[-2000:]
        assert 3 < time.time() - t0 and count(game, MILITIA) == militia    # the chat at 5 s, the militia not yet
        assert wait(lambda: count(game, MILITIA) == militia + 1, 15)       # the militia at 10 s
        assert 8 < time.time() - t0
        assert count(game, ARCHERS) > 0
        assert wait(lambda: count(game, ARCHERS) == 0, 60)                 # "Archer leaves" at 60 s
        assert 58 < time.time() - t0
        assert datapack_problems(game.server.log) == []
