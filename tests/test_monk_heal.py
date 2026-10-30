"""game/monk.py: an idle own monk heals the nearest injured own unit in 4 tiles, 150 hit points per AoE2 minute, up to
max_health; no heal for itself, siege units, ships, enemy units, or from a monk that walks (#1244)."""
import re

import pytest
from test_cheat_transform import HurtServer
from test_gather import grid

from game import gather, monk


class HealServer(HurtServer):
    """A HurtServer that also takes `data modify entity <uuid> Health set value <hp>f`."""

    def command(self, cmd):
        if m := re.fullmatch(r"data modify entity (\S+) Health set value ([\d.]+)f", cmd):
            self.log.append(cmd)
            self.entities[m[1]]["Health"] = float(m[2])
            return ""
        return super().command(cmd)


def setup(*others):
    """A flat 24 × 24 map (tile size 1) with an own monk "monk" at block (5.5, 5.5) and the units of `others`:
    (uuid, name, player, x, health, max)."""
    objects = [{"kind": "unit", "name": "MONK", "player": 1, "uuid": "monk", "tile": [5.5, 5.5]}]
    ents = {"monk": {"Pos": (5.5, 64.0, 5.5), "Health": 10.0, "Max": 30.0}}
    for uuid, name, player, x, hp, top in others:
        objects.append({"kind": "unit", "name": name, "player": player, "uuid": uuid, "tile": [x, 5.5]})
        ents[uuid] = {"Pos": (x, 64.0, 5.5), "Health": hp, "Max": top}
    server = HealServer(ents)
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    return server, g


def run(g, seconds):
    """seconds AoE2 seconds of heal passes, after a first pass that sees the monk stand."""
    if "monk" not in g.monk_at:
        monk.heal(g, monk.EVERY)
    for _ in range(round(seconds / monk.EVERY)):
        monk.heal(g, monk.EVERY)


def test_the_monk_heals_150_hit_points_per_minute_up_to_max_health():
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0))
    run(g, 4)
    assert server.entities["a"]["Health"] == pytest.approx(10 + 4 * 2.5)
    run(g, 60)
    assert server.entities["a"]["Health"] == 40.0
    assert server.entities["monk"]["Health"] == 10.0                  # a monk does not heal itself


def test_no_heal_out_of_range_for_siege_ships_and_enemies():
    server, g = setup(("far", "MILITIA", 1, 9.6, 10.0, 40.0), ("ram", "BATTERING_RAM", 1, 6.5, 10.0, 175.0),
                      ("ship", "GALLEY", 1, 6.5, 10.0, 120.0), ("foe", "MILITIA", 2, 6.5, 10.0, 40.0))
    g.soldiers.update(ram="BATTERING_RAM", ship="GALLEY")
    run(g, 10)
    assert [e["Health"] for e in server.entities.values()] == [10.0] * 5
    assert not monk.healable("BATTERING_RAM") and not monk.healable("GALLEY") and monk.healable("VILLAGER_MALE")


def test_one_monk_heals_one_unit_the_nearest():
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0), ("v", "VILLAGER_MALE", 1, 6.5, 20.0, 25.0))
    run(g, 2)
    assert server.entities["v"]["Health"] == 25.0 and server.entities["a"]["Health"] == 10.0
    run(g, 2)                                                          # the villager has full health: the next one
    assert server.entities["a"]["Health"] == 15.0


def test_a_second_monk_heals_another_unit_and_a_monk_heals_a_monk():
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0), ("monk2", "MONK", 1, 7.5, 20.0, 30.0))
    run(g, 2)
    assert server.entities["monk2"]["Health"] == 25.0                 # the first monk heals the nearest: the monk
    assert server.entities["a"]["Health"] == 15.0                     # the second monk heals the militia
    assert server.entities["monk"]["Health"] == 15.0 - 5.0            # ... and not the first monk (it is taken)


def test_a_monk_that_walks_does_not_heal():
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0))
    for i in range(5):
        server.entities["monk"]["Pos"] = (5.5 + i, 64.0, 5.5)
        monk.heal(g, monk.EVERY)
    assert server.entities["a"]["Health"] == 10.0


def test_the_step_calls_the_heal_in_aoe2_seconds():
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0))
    for _ in range(16):                                                # 4 real seconds at Normal speed
        g.step()
    assert server.entities["a"]["Health"] == pytest.approx(10 + 2.5 * (4 * gather.NORMAL - 1), abs=2.5)


@pytest.mark.mc
def test_a_monk_heals_an_own_militia_and_not_an_enemy_on_a_server(tmp_path):
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
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=8, y=6)
    scn.unit_manager.add_unit(scenarios.PlayerId.TWO, UnitInfo.MILITIA.ID, x=6, y=8)
    src = str(tmp_path / "monk.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        own, = [u for u, n in g.soldiers.items() if n == "MILITIA"]
        foe, = g.enemies
        for u in (own, foe):
            game.command(f"data modify entity {u} Health set value 10.0f")
        t0 = time.monotonic()
        while time.monotonic() - t0 < 4:
            g.step()
            time.sleep(g.tick)
        hp, top = monk.health(g, own)
        game_seconds = (time.monotonic() - t0) * gather.NORMAL
        assert 10 + 2.5 * (game_seconds - 3) <= hp <= min(top, 10 + 2.5 * game_seconds), (hp, game_seconds)
        assert monk.health(g, foe)[0] == 10.0
