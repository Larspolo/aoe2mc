"""game/monk.py: a selected monk converts an enemy unit in AoE2 time (#1245): it walks into 9 tiles, then converts
after 5 to 9 intervals of 1.25 AoE2 seconds and rests 62 seconds; no conversion of a monk, king, hero or siege unit."""
import pytest
from test_gather import FakeServer, grid

from game import gather, monk


def setup(*others):
    """A flat 40 × 40 map (tile size 1) with an own monk "monk" at block (5.5, 5.5) and the units of `others`:
    (uuid, name, player, x[, hero])."""
    objects = [{"kind": "unit", "name": "MONK", "player": 1, "uuid": "monk", "tile": [5.5, 5.5]}]
    ents = {"monk": {"Pos": (5.5, 64.0, 5.5)}}
    for uuid, name, player, x, *hero in others:
        objects.append({"kind": "unit", "name": name, "player": player, "uuid": uuid, "tile": [x, 5.5]} |
                       ({"hero": True} if hero else {}))
        ents[uuid] = {"Pos": (x, 64.0, 5.5)}
    server = FakeServer(ents)
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    return server, g


def until_converted(g, uuid, limit=20):
    """AoE2 seconds of conversion passes of a quarter second until unit uuid is no enemy (at most limit seconds)."""
    t = 0.0
    while uuid in g.enemies and t < limit:
        monk.convert(g, 0.25)
        t += 0.25
    return t


def test_a_monk_converts_an_enemy_in_5_to_9_intervals():
    times = []
    for seed in range(40):
        server, g = setup(("foe", "MILITIA", 2, 12.5))
        g.chance.seed(seed)
        assert monk.convert_order(g, {"monk"}, "foe")
        times.append(until_converted(g, "foe"))
        assert "foe" in g.soldiers and "foe" not in g.converting
        assert {"tag foe remove aoe2mc.p2", "tag foe add aoe2mc.p1", "team join p1 foe", "aoe stop foe"} <= set(server.log)
        assert "execute as foe on vehicle run team join p1 @s" in server.log    # a horse or a boat too
        assert any(c.startswith("data modify entity foe CustomName.color") for c in server.log)
    assert min(times) >= 5 * monk.INTERVAL and max(times) <= 9 * monk.INTERVAL
    assert len(set(times)) > 2                                         # a chance, not a fixed time


def test_a_monk_out_of_range_walks_to_the_target():
    server, g = setup(("foe", "MILITIA", 2, 20.5))
    monk.convert_order(g, {"monk"}, "foe")
    monk.convert(g, 5.0)
    assert "aoe moveto monk 20.5 64.0 5.5" in server.log and "foe" in g.enemies
    server.entities["monk"]["Pos"] = (21.0 - monk.MONKS["MONK"], 64.0, 5.5)   # in its range now: it stops and converts
    assert until_converted(g, "foe") <= 9 * monk.INTERVAL
    assert "aoe stop monk" in server.log


def test_a_converted_villager_gathers_for_the_new_player():
    server, g = setup(("v", "VILLAGER_FEMALE", 2, 10.5))
    monk.convert_order(g, {"monk"}, "v")
    until_converted(g, "v")
    assert "v" in g.villagers and "v" not in g.soldiers and any(o["uuid"] == "v" for o in g.units)


def test_no_conversion_of_a_monk_king_hero_or_siege_unit():
    server, g = setup(("m", "MONK", 2, 8.5), ("k", "KING", 2, 8.5), ("r", "BATTERING_RAM", 2, 8.5),
                      ("h", "WILLIAM_WALLACE", 2, 8.5, True), ("s", "SPEARMAN", 2, 8.5))
    assert [monk.convert_order(g, {"monk"}, u) for u in "mkrhs"] == [False] * 4 + [True]


def test_the_monk_rests_62_seconds_after_a_conversion():
    server, g = setup(("a", "MILITIA", 2, 8.5), ("b", "MILITIA", 2, 9.5))
    monk.convert_order(g, {"monk"}, "a")
    until_converted(g, "a")
    monk.convert_order(g, {"monk"}, "b")
    assert until_converted(g, "b", limit=monk.REST - 1) == pytest.approx(monk.REST - 1)
    assert until_converted(g, "b") <= 1 + 9 * monk.INTERVAL


def test_the_monk_does_not_attack_and_does_not_heal_while_it_converts():
    server, g = setup(("a", "MILITIA", 2, 8.5), ("own", "MILITIA", 1, 6.5))
    g.choose({"monk", "own"})
    g.attack("a")
    assert "aoe attack own a" in server.log and not any(c.startswith("aoe attack monk") for c in server.log)
    monk.convert_order(g, g.monks(), "a")
    assert g.converting == {"monk": ["a", 0.0, 0]}


@pytest.mark.mc
def test_a_monk_converts_an_enemy_militia_on_a_server(tmp_path):
    import contextlib
    import io
    import json
    import time

    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import run
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.MONK.ID, x=6, y=6)
    scn.unit_manager.add_unit(scenarios.PlayerId.TWO, UnitInfo.MILITIA.ID, x=8, y=8)
    src = str(tmp_path / "monk.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        own, = [u for u, n in g.soldiers.items() if n == "MONK"]
        foe, = g.enemies
        g.choose({own})
        assert monk.convert_order(g, g.monks(), foe)
        t0 = time.monotonic()
        while foe in g.enemies and time.monotonic() - t0 < 30:
            g.step()
            time.sleep(g.tick)
        game_seconds = (time.monotonic() - t0) * gather.NORMAL
        assert foe in g.soldiers and 5 * monk.INTERVAL <= game_seconds, game_seconds
        assert "Test passed" in game.command(f"execute as {foe} if entity @s[team=p1,tag=aoe2mc.p1,tag=!aoe2mc.p2]")
        assert "#" in game.command(f"data get entity {foe} CustomName.color")
