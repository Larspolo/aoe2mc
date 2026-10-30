"""game/trebuchet.py: a packed trebuchet with an attack order on a target out of its range walks packed until the
target is in range, and unpacks there, as in AoE2 DE (#1400). Fake server; an mc test on Paper."""
import contextlib
import io
import json
import math
import time

import pytest
from test_train_castle import setup

from game import ai, combat, gather, run, train, trebuchet


def treb(at=(2.5, 64.0, 20.5), enemy=(22.5, 64.0, 20.5)):
    """A packed own trebuchet "t" and an enemy unit "e" 20 blocks away (tile size 1: range 16 blocks)."""
    server, g = setup()
    server.entities.update(t={"Pos": at}, e={"Pos": enemy})
    g.soldiers["t"] = "TREBUCHET"
    trebuchet.tick(g, 0.0)
    g.choose({"t"}, "t")
    server.log.clear()
    return server, g


def test_a_far_target_the_trebuchet_walks_packed_and_unpacks_in_range():
    server, g = treb()
    g.attack("e")
    walk = ai.speed_command("t", "TREBUCHET", g.map.T, gather.NORMAL * train.speed(g, "TREBUCHET"))
    assert [c for c in server.log if c.startswith("aoe ")] == [walk, "aoe moveto t 22.5 64.0 20.5"]
    assert trebuchet.state(g, "t") == "walking"
    server.entities["t"]["Pos"] = (6.5, 64.0, 20.5)                   # 16 blocks: not yet MARGIN inside the range
    trebuchet.tick(g, 1.0)
    assert trebuchet.state(g, "t") == "walking" and "aoe stop t" not in server.log
    server.entities["t"]["Pos"] = (7.5, 64.0, 20.5)                   # 15 blocks
    trebuchet.tick(g, 1.0)
    assert server.log[-2:] == ["aoe stop t", "aoe speed t 0"] and trebuchet.state(g, "t") == "unpacking"
    trebuchet.tick(g, trebuchet.PACK)
    assert server.log[-2:] == [combat.range_command("t", "TREBUCHET", g.map.T), "aoe attack t e"]
    assert trebuchet.state(g, "t") == "unpacked"


def test_a_target_in_range_it_unpacks_at_once():
    server, g = treb(enemy=(12.5, 64.0, 20.5))
    g.attack("e")
    assert [c for c in server.log if c.startswith("aoe ")] == ["aoe stop t", "aoe speed t 0"]
    assert trebuchet.state(g, "t") == "unpacking"


def test_an_unpacked_trebuchet_packs_first_for_a_far_target():
    server, g = treb(enemy=(12.5, 64.0, 20.5))
    g.attack("e")
    trebuchet.tick(g, trebuchet.PACK)
    server.entities["e"]["Pos"] = (22.5, 64.0, 20.5)
    server.log.clear()
    g.attack("e")
    assert server.log[-2:] == ["aoe stop t", trebuchet.range_command(g, "t", 0)] and trebuchet.state(g, "t") == "packing"
    trebuchet.tick(g, trebuchet.PACK)
    assert server.log[-1] == "aoe moveto t 22.5 64.0 20.5" and trebuchet.state(g, "t") == "walking"


def test_it_follows_a_moved_target_and_stops_when_the_target_is_gone():
    server, g = treb()
    g.attack("e")
    server.entities["e"]["Pos"] = (23.5, 64.0, 20.5)                  # 1 block: the same walk
    trebuchet.tick(g, 1.0)
    assert server.log.count("aoe moveto t 22.5 64.0 20.5") == 1 and not any("23.5" in c for c in server.log)
    server.entities["e"]["Pos"] = (22.5, 64.0, 23.5)                  # 3 blocks
    trebuchet.tick(g, 1.0)
    assert server.log[-1] == "aoe moveto t 22.5 64.0 23.5"
    del server.entities["e"]
    trebuchet.tick(g, 1.0)
    assert server.log[-1] == "aoe stop t" and trebuchet.state(g, "t") == "packed"


def test_the_range_to_a_building_counts_from_its_nearest_block():
    server, g = treb()
    g.forts["fort"] = (18, 64, 18, 21, 69, 22)                         # blocks x 18-21: the near edge at x 18
    assert trebuchet.gap(g, "t", "fort") == (18 - 2.5 - (16 - trebuchet.MARGIN), (20.0, 64, 20.5))
    g.attack("fort")
    assert trebuchet.state(g, "t") == "unpacking"                    # 15.5 blocks: in range
    server, g = treb(at=(1.5, 64.0, 20.5))
    g.forts["fort"] = (18, 64, 18, 21, 69, 22)
    g.attack("fort")
    assert trebuchet.state(g, "t") == "walking" and server.log[-1] == "aoe moveto t 20.0 64 20.5"


@pytest.mark.mc
def test_a_trebuchet_walks_to_a_building_20_tiles_away_and_hurts_it(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(40)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.TREBUCHET.ID, x=6.5, y=20.5)
    um.add_unit(scenarios.PlayerId.TWO, BuildingInfo.BARRACKS.ID, x=28.5, y=20.5)   # its near edge: 20.5 tiles
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
        assert trebuchet.state(g, t) == "walking"
        hp, states = combat.stats("BARRACKS").hp, []
        full = hp
        end = time.time() + 120
        while hp == full:
            assert time.time() < end, (states, g.pos(t))
            g.step()
            states += [trebuchet.state(g, t)][:not states or states[-1] != trebuchet.state(g, t)]
            time.sleep(g.tick)
            out = game.command(f"scoreboard players get {fort} aoe_hp")
            hp = int(out.split(" has ")[1].split()[0]) if " has " in out else hp
        moved = math.dist(g.pos(t), start)
        assert states == ["walking", "unpacking", "unpacked"] and 3 * g.map.T < moved, (states, moved)
