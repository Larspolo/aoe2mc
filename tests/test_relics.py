"""game/monk.py: a monk picks up a relic, carries it into an own monastery, and each relic there gives gold
(monk.GOLD); a monk with a relic does not heal, and a killed monk drops it (#1246). Fake server."""
import pytest
from test_monk_heal import HealServer
from test_gather import grid

from game import gather, monk

MONASTERY = [14, 2, 18, 6]                                             # block footprint x0, z0, x1, z1


def setup():
    """A flat 24 × 24 map (tile size 1): an own monk at (5.5, 5.5), a relic at block (10, 5), an own monastery."""
    objects = [{"kind": "unit", "name": "MONK", "player": 1, "uuid": "monk", "tile": [5.5, 5.5]},
               {"kind": "other", "name": "RELIC", "player": 0, "tile": [10.5, 5.5]},
               {"kind": "building", "name": "MONASTERY", "player": 1, "footprint": MONASTERY}]
    server = HealServer({"monk": {"Pos": (5.5, 64.0, 5.5), "Health": 30.0, "Max": 30.0}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.paper = True
    g.choose({"monk"}, "monk")
    return server, g


def walk(server, g, x, z):
    """The monk stands at block (x, z); one relic pass."""
    server.entities["monk"]["Pos"] = (x, 64.0, z)
    monk.relic_tick(g, monk.EVERY)


def carry(server, g):
    assert monk.order(g, "Steve", (10, 6))                             # one block next to the pot: still the relic
    assert g.fetching == {"monk": ("relic", 0)}
    walk(server, g, 10.5, 6.5)
    assert monk.carriers(g) == {"monk": 0} and g.relics[0]["at"] is None
    assert "fill 10 63 5 10 65 5 air replace minecraft:decorated_pot" in server.log
    assert "ride @e[type=item_display,tag=aoe_relic_0,limit=1] mount monk" in server.log


def test_the_monk_picks_up_the_relic_and_carries_it_into_the_monastery():
    server, g = setup()
    carry(server, g)
    assert monk.order(g, "Steve", (15, 3))                             # a click on the monastery
    to = next(iter(g.map.front((14, 18, 2, 6))))
    walk(server, g, to[0] + 0.5, to[1] + 0.5)
    assert g.relics[0]["home"] == (14, 18, 2, 6) and not monk.carriers(g)
    assert "kill @e[type=item_display,tag=aoe_relic_0]" in server.log


def test_a_relic_in_the_monastery_gives_gold():
    server, g = setup()
    g.relics[0].update(at=None, home=(14, 18, 2, 6))
    gold = g.stock["gold"]
    for _ in range(60):
        monk.relic_tick(g, monk.EVERY)
    assert g.stock["gold"] - gold == round(monk.GOLD * monk.EVERY * 60) > 0
    assert f"scoreboard players add Gold {g.board} 1" in server.log


def test_no_order_without_a_monk_or_far_from_the_relic():
    server, g = setup()
    assert not monk.order(g, "Steve", (12, 5))                         # two blocks away
    g.choose(set(), None)
    assert not monk.order(g, "Steve", (10, 5))


def test_a_monk_with_a_relic_does_not_heal():
    server, g = setup()
    carry(server, g)
    assert "monk" not in {u for u, n in g.soldiers.items() if n == "MONK"} - set(monk.carriers(g))


def test_a_killed_monk_drops_the_relic_at_its_place():
    server, g = setup()
    carry(server, g)
    walk(server, g, 7.5, 9.5)
    del server.entities["monk"]
    monk.relic_tick(g, monk.EVERY)
    assert g.relics[0] == {"at": (7, 9), "monk": None, "home": None}
    assert "setblock 7 64 9 minecraft:decorated_pot keep" in server.log


@pytest.mark.parametrize("cell", [(10, 5), (11, 4)])
def test_a_dropped_relic_can_be_picked_up_again(cell):
    server, g = setup()
    g.relics[0]["at"] = cell
    assert monk.order(g, "Steve", (10, 5))


@pytest.mark.mc
def test_a_monk_carries_a_relic_into_a_monastery_on_a_server(tmp_path):
    import contextlib
    import io
    import json
    import time

    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    from game import run
    scn = scenarios.new_scenario(16)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.MONK.ID, x=4.5, y=4.5)
    um.add_unit(scenarios.PlayerId.GAIA, OtherInfo.RELIC.ID, x=4.5, y=8.5)
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.MONASTERY.ID, x=10, y=5)
    src = str(tmp_path / "relic.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)

    def until(done, seconds=40):
        t0 = time.monotonic()
        while not done() and time.monotonic() - t0 < seconds:
            g.step()
            time.sleep(g.tick)
        return done()

    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        assert g.paper
        m, = [u for u, n in g.soldiers.items() if n == "MONK"]
        (x, z), = [r["at"] for r in g.relics]
        y = g.map.y(x, z)
        pot = [h for h in (y - 1, y, y + 1) if "passed" in game.command(f"execute if block {x} {h} {z} {monk.POT}")]
        assert pot, "no relic block"
        g.choose({m}, m)
        assert monk.order(g, "nobody", (x, z))
        assert until(lambda: monk.carriers(g)), "the monk did not pick up the relic"
        assert "passed" not in game.command(f"execute if block {x} {pot[0]} {z} {monk.POT}")
        assert "passed" in game.command("execute as @e[type=item_display,tag=aoe_relic_0] on vehicle if entity @s[type=!item_display]")
        rect, = monk.monasteries(g)
        assert monk.order(g, "nobody", (rect[0] + 1, rect[2] + 1))
        assert until(lambda: g.relics[0]["home"]), "the monk did not put the relic in"
        gold = g.stock["gold"]
        assert until(lambda: g.stock["gold"] > gold, 5)
        assert "passed" not in game.command("execute if entity @e[type=item_display,tag=aoe_relic_0]")
