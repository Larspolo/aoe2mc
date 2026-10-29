"""game/trebuchet.py: the castle trains the trebuchet in the Imperial Age, and it packs and unpacks as in AoE2 DE
(#1351): an attack order unpacks it (11.1 AoE2 s), a move order packs it. Fake server; an mc test on Paper."""
import contextlib
import io
import json
import math
import time

import pytest
from test_train_castle import menus, setup
from test_train_menu import entry

from game import ai, build, combat, gather, run, train, trebuchet


def test_the_castle_trains_the_trebuchet_only_in_the_imperial_age():
    cost = train.COSTS["TREBUCHET"]
    server, g = setup(wood=cost.get("wood", 0), gold=cost.get("gold", 0))   # the Castle Age
    assert [n for n in train.trains(g, "CASTLE") if not train.value("civ", n)] == ["LONGBOWMAN", *train.TRAINS["CASTLE"]]  # Britons: no unique technologies (#4103, #4283)
    rect = train.open_menu(g, "Steve", (12, 4))
    assert f" {entry(g, rect, 'TREBUCHET')}{build.locked(g, 'TREBUCHET')}" in menus(server)[-1]
    assert train.queue(g, "Steve", (12, 4), "TREBUCHET") is None
    server, g = setup(wood=cost.get("wood", 0), gold=cost.get("gold", 0), ages=3)
    assert train.queue(g, "Steve", (12, 4), "TREBUCHET") and (g.stock["wood"], g.stock["gold"]) == (0, 0)


def treb(server, g):
    """An own trebuchet "t" of g, as tick() finds it: packed, range 0."""
    g.soldiers["t"] = "TREBUCHET"
    trebuchet.tick(g, 0.0)
    assert server.log[-1] == trebuchet.range_command(g, "t", 0)
    assert trebuchet.state(g, "t") == "packed"


def test_an_attack_order_stops_the_walk_and_shoots_after_the_unpack_time():
    server, g = setup()
    treb(server, g)
    g.choose({"t"}, "t")
    server.log.clear()
    g.attack("fort")                                                  # no position: in range (#1400)
    assert [c for c in server.log if c.startswith("aoe ")][:2] == ["aoe stop t", "aoe speed t 0"]
    assert trebuchet.state(g, "t") == "unpacking"
    assert not any(c.startswith(("aoe attack", "aoe range")) for c in server.log)
    trebuchet.tick(g, 11.0)
    assert not any(c.startswith(("aoe attack", "aoe range")) for c in server.log)
    trebuchet.tick(g, 0.2)
    assert server.log[-2:] == [combat.range_command("t", "TREBUCHET", g.map.T), "aoe attack t fort"]
    assert trebuchet.state(g, "t") == "unpacked"
    g.attack("other")                                                 # unpacked: at once
    assert server.log[-1] == "aoe attack t other"


def test_a_move_order_packs_it_and_it_walks_after_the_pack_time():
    server, g = setup()
    treb(server, g)
    server.log.clear()
    ai.move(g, "t", "TREBUCHET", g.map.T, 5.5, 64, 5.5)                 # packed: it walks at once
    assert server.log == [ai.speed_command("t", "TREBUCHET", g.map.T), "aoe moveto t 5.5 64 5.5"]
    trebuchet.unpack(g, "t", "fort")
    trebuchet.tick(g, trebuchet.PACK)
    server.log.clear()
    ai.move(g, "t", "TREBUCHET", g.map.T, 5.5, 64, 5.5)
    assert server.log == ["aoe stop t", trebuchet.range_command(g, "t", 0)] and trebuchet.state(g, "t") == "packing"
    trebuchet.tick(g, 11.0)
    assert not any(c.startswith("aoe moveto") for c in server.log)
    trebuchet.tick(g, 0.2)
    assert server.log[-2:] == [ai.speed_command("t", "TREBUCHET", g.map.T), "aoe moveto t 5.5 64 5.5"]
    assert trebuchet.state(g, "t") == "packed"


def test_a_dead_trebuchet_is_forgotten():
    server, g = setup()
    treb(server, g)
    del g.soldiers["t"]
    trebuchet.tick(g, 1.0)
    assert "t" not in g.trebs


@pytest.mark.mc
def test_an_unpacked_trebuchet_hurts_a_building_at_12_tiles_and_does_not_move(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    scn = scenarios.new_scenario(32)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.TREBUCHET.ID, x=6.5, y=16.5)
    um.add_unit(scenarios.PlayerId.TWO, BuildingInfo.BARRACKS.ID, x=20.5, y=16.5)   # its near edge: 12.5 tiles
    src = str(tmp_path / "t.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        t, = [u for u, n in g.soldiers.items() if n == "TREBUCHET"]
        fort, = g.fort_names
        start = g.pos(t)
        g.step()                                                     # packed: range 0
        g.choose({t}, t)
        g.attack(fort)
        hp = full = combat.stats("BARRACKS").hp
        end = time.time() + 60
        while hp == full:
            assert time.time() < end, (trebuchet.state(g, t), g.pos(t))
            g.step()
            time.sleep(g.tick)
            out = game.command(f"scoreboard players get {fort} aoe_hp")
            hp = int(out.split(" has ")[1].split()[0]) if " has " in out else hp
        assert hp < full and math.dist(g.pos(t), start) < 0.5, (hp, g.pos(t), start)
