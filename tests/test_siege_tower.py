"""game/siege_tower.py: up to siege_tower.SIZE infantry, foot archers or villagers ride a siege tower and come out
next to it (#1362). Fake server; an mc test on Paper."""
import contextlib
import io
import json
import time

import pytest
from test_gather import FakeServer, grid

from game import combat, garrison, gather, run, siege_tower

UNITS = {"tower": ("SIEGE_TOWER", 12.5), "m": ("MILITIA", 4.5), "a": ("ARCHER", 5.5), "s": ("SCOUT_CAVALRY", 6.5)}


def setup():
    """A flat 24 × 24 map (tile size 1): an own siege tower at (12.5, 12.5), a militia, an archer, a scout cavalry and a
    villager "v" in the row z = 4.5. All are selected."""
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [x, 4.5 if u != "tower" else 12.5]}
               for u, (n, x) in UNITS.items()]
    objects.append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 4.5]})
    ents = {o["uuid"]: {"Pos": (o["tile"][0], 64.0, o["tile"][1])} for o in objects}
    server = FakeServer(ents)
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={}).setup()
    g.paper = True
    g.choose({"m", "a", "s", "v"}, "m")
    return server, g


def test_infantry_foot_archers_and_villagers_walk_into_the_tower_and_ride_it():
    server, g = setup()
    assert siege_tower.order(g, "Steve", "tower")
    assert g.boarding == {"m": "tower", "a": "tower", "v": "tower"}     # not the scout cavalry
    assert "aoe moveto m 12.5 64.0 12.5" in server.log and not any(c.startswith("aoe moveto s ") for c in server.log)
    for u in ("m", "a"):
        server.entities[u]["Pos"] = (13.5, 64.0, 13.5)
    server.log.clear()
    siege_tower.tick(g)
    assert server.log.index("execute as tower on passengers run ride a mount @s") < server.log.index("ride m mount a")
    assert f"data merge entity m {garrison.INSIDE}" in server.log and "aoe hide @a m" in server.log
    assert g.towers == {"tower": ["a", "m"]} and g.boarding == {"v": "tower"}
    assert {"a", "m"} <= garrison.inside(g) and not {"a", "m"} & g.selected


def test_a_full_tower_takes_no_more_and_a_click_on_it_lets_them_out():
    server, g = setup()
    g.towers = {"tower": [f"x{k}" for k in range(siege_tower.SIZE - 1)]}
    siege_tower.order(g, "Steve", "tower")
    for u in ("m", "a"):
        server.entities[u]["Pos"] = (13.5, 64.0, 13.5)
    siege_tower.tick(g)
    assert g.towers["tower"][-1] == "a" and len(g.towers["tower"]) == siege_tower.SIZE   # the militia stays outside
    server.log.clear()
    assert len(siege_tower.out(g, "tower")) == siege_tower.SIZE and "tower" not in g.towers
    assert server.log[1] == "ride a dismount" and "aoe show @a a" in server.log      # after the read of its place
    assert f"data merge entity a {garrison.OUTSIDE}" in server.log
    assert any(c.startswith("tellraw") and f"{siege_tower.SIZE} units came out" in c for c in server.log)


def test_the_units_of_a_dead_tower_come_out_where_they_are():
    server, g = setup()
    g.towers = {"tower": ["m"]}
    server.entities["m"]["Pos"] = (12.5, 65.0, 12.5)
    del g.soldiers["tower"]
    siege_tower.tick(g)
    assert not g.towers and "ride m dismount" in server.log


@pytest.mark.mc
def test_a_militia_rides_a_siege_tower_on_paper(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(24)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.SIEGE_TOWER.ID, x=12.5, y=12.5)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=8.5, y=12.5)
    src = str(tmp_path / "s.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        tower, = [u for u, n in g.soldiers.items() if n == "SIEGE_TOWER"]
        militia, = [u for u, n in g.soldiers.items() if n == "MILITIA"]
        g.choose({militia}, militia)
        assert siege_tower.order(g, "nobody", tower)
        end = time.time() + 60
        while not vars(g).get("towers"):
            assert time.time() < end, (g.pos(militia), g.pos(tower))
            g.step()
            time.sleep(g.tick)
        assert "Test passed" in game.command(f"execute as {tower} on passengers if entity @s[nbt={{Passengers:[{{}}]}}]")
        assert game.command(f"data get entity {militia} Invulnerable").strip().endswith("1b")
        siege_tower.out(g, tower)
        time.sleep(1)
        assert "Test passed" not in game.command(f"execute as {tower} on passengers if entity @s[nbt={{Passengers:[{{}}]}}]")
        assert game.command(f"data get entity {militia} Invulnerable").strip().endswith("0b")
