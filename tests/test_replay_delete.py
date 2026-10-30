"""Live replay: a DELETE removes its units and buildings (#630). Fake RCON."""
import contextlib
import io
import json
import os
import re
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_walk import VIL, play, tps  # noqa: E402


def delete(t, objects, names=None, player=1):
    e = dict(time=t, player=player, kind="delete", objects=list(objects))
    if names:
        e["names"] = names
    return e


def test_a_deleted_unit_dies_and_later_moves_skip_it():
    tl = [dict(time=0, player=1, kind="move", objects=[7], tile=[0.5, 10.5]), delete(400, [7]),
          dict(time=2000, player=1, kind="move", objects=[7], tile=[14.5, 2.5])]
    r, sent, _ = play(tl)
    k = sent.index("kill u1")
    assert 7 not in r.units and not r.moving
    assert not tps(sent[k + 1:]) and len(tps(sent[:k])) <= 2           # 400 ms: at most one step before it dies


def test_a_deleted_building_falls_and_frees_its_cells():
    r, sent, _ = play([delete(0, [9])])
    fills = [re.match(r"fill (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) air destroy$", c) for c in sent]
    boxes = [tuple(int(v) for v in m.groups()) for m in fills if m]
    assert boxes and all(b[0] == 20 and b[2] == 36 and b[3] == 27 and b[5] == 47 for b in boxes)   # [20, 36, 28, 48)
    assert boxes[0][1] == 70 and boxes[-1][4] >= 70 + replay.TALL - 1
    assert all(r.map.free(x, z) for x in range(20, 28) for z in range(36, 48))
    assert 9 not in r.refs and not any(s[0] == 9 for s in r.starts)


def test_a_deleted_new_building_falls_to_its_top():
    tl = [dict(time=0, player=1, kind="build", type=70, name="HOUSE", tile=[12.0, 4.0]),
          delete(500, [900], names=["HOUSE"])]
    r, sent, _ = play(tl, objects=[VIL])
    assert not r.placed and r.map.free(48, 16)
    falls = [c for c in sent if c.endswith(" air destroy")]
    assert falls and all(c.split()[1] == "44" and c.split()[3] == "12" for c in falls)


def test_an_unknown_id_gives_no_command():
    r = replay.Replay(Fake(), data([]))
    assert r.commands(delete(0, [12345])) == [] and r.commands(delete(0, [12345], names=["HOUSE"])) == []


@pytest.mark.mc
def test_a_deleted_unit_and_building_are_gone_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import run
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.HOUSE.ID, x=6, y=6)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=10.5, y=10.5)
    src = str(tmp_path / "delete.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        d = json.load(f)
    house = next(o for o in d["objects"] if o["name"] == "HOUSE")
    vil = next(o for o in d["objects"] if o["kind"] == "unit")
    house["ref"], vil["ref"] = 1, 2                                     # the object IDs of a record
    x0, z0, x1, z1 = house["footprint"]
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        assert "passed" in game.command(f"execute if entity {vil['uuid']}")
        r = replay.Replay(game, d)
        solid = [(x, y, z) for x in range(x0, x1) for z in range(z0, z1) for y in range(60, 80)
                 if "failed" in game.command(f"execute if block {x} {y} {z} air")]
        assert solid
        r.send(r.commands(delete(0, [1, 2])))
        end = time.time() + 10                                          # the death animation: 20 ticks
        while "passed" in game.command(f"execute if entity {vil['uuid']}"):
            assert time.time() < end, "the villager is not dead"
            time.sleep(0.25)
        ground = min(r.map.y(x, z) for x, z in r.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)}))
        left = [p for p in solid if p[1] >= ground and "failed" in game.command("execute if block {} {} {} air".format(*p))]
        assert not left, f"blocks of the house stay: {left[:5]}"
