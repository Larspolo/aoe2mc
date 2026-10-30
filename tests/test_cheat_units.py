"""game/cheats.py: a unit cheat summons its unit at the town center of the player (#818)."""
import pytest
from test_gather import FakeServer, grid
from test_train import setup

from game import cheats, combat, gather

UNITS = {c: e.name for c, e in cheats.CODES.items() if isinstance(e, cheats.Unit)}


@pytest.mark.parametrize("code", sorted(UNITS))
def test_a_unit_cheat_summons_its_unit_at_the_own_town_center(code):
    server, g = setup()
    g.cheats = True
    server.scores["aoe_cheat"] = cheats.NAMES.index(code) + 1
    assert cheats.clicks(g) == [("Steve", code)]
    summons = [c for c in server.log if c.startswith("summon ")]
    assert len(summons) == 1
    x, z = (float(v) for v in summons[0].split()[2:5:2])
    assert 1 <= x <= 7 and 1 <= z <= 7                                 # next to the town center of player 1 (2-4)
    assert any(c.startswith("aoe stats ") for c in server.log)        # the AoE2 values (combat.STATS)
    assert list(g.soldiers.values()) == [UNITS[code]] and not g.stock["food"] < 60   # it costs nothing


def test_the_cheat_units_have_their_aoe2_values():
    server, g = setup()
    g.cheats = True
    server.scores["aoe_cheat"] = cheats.NAMES.index("how do you turn this on") + 1
    cheats.clicks(g)
    stats = next(c for c in server.log if c.startswith("aoe stats "))
    assert stats == combat.stats_command(stats.split()[2], UNITS["how do you turn this on"])


def test_no_unit_without_a_town_center():
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), cheats=True).setup()
    server.scores["aoe_cheat"] = cheats.NAMES.index("catzor") + 1
    assert cheats.clicks(g) == [("Steve", "catzor")]
    assert not any(c.startswith("summon ") for c in server.log) and not g.soldiers


def test_no_unit_with_cheats_off():
    server, g = setup()
    server.scores["aoe_cheat"] = cheats.NAMES.index("catzor") + 1
    assert cheats.clicks(g) == []
    assert not any(c.startswith("summon ") for c in server.log)


@pytest.mark.mc
def test_cheat_units_appear_and_walk_to_an_order_on_a_server(tmp_path):
    """The War Penguin walks to an `aoe moveto` order. The Cobra car appears; it is a minecart (as all siege units),
    and the plugin moves only mobs: #836."""
    import contextlib
    import io
    import json
    import time

    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo

    import aoe2mc
    from game import ai, run
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=4, y=4)
    src = str(tmp_path / "cheat.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, cheats=True).setup()
        for code in ("how do you turn this on", "i don't exist"):
            cheats.apply(g, "nobody", code)
        cobra, penguin = g.soldiers
        assert g.pos(cobra), "the Cobra car exists"
        start = g.pos(penguin)
        goal = (40.5, g.map.y(40, 40), 40.5)
        assert "Moved 1 units" in ai.move(game, penguin, "WAR_PENGUIN", g.map.T, *goal)
        end = time.time() + 60
        while (p := g.pos(penguin)) and (p[0] - goal[0]) ** 2 + (p[2] - goal[2]) ** 2 > 2 ** 2:
            assert time.time() < end, f"the War Penguin is at {p}, not at {goal} (from {start})"
            time.sleep(0.5)
