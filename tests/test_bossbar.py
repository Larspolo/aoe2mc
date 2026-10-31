"""game/bossbar.py: the boss bar of the selected unit shows its name, the number of selected units and its hit points
(#659)."""
import pytest
from test_gather import FakeServer, grid

from game import bossbar, gather


class Server(FakeServer):
    """FakeServer with the Health of each entity in the bossbar store commands."""

    def command(self, cmd):
        out = super().command(cmd)
        if cmd.startswith("execute store result bossbar") and " Health" in cmd:
            uuid = cmd.split()[-2]
            hp = self.entities[uuid].get("Health", 40.0) if uuid in self.entities else None
            return "No entity was found" if hp is None else f"{uuid} has the following entity data: {hp}f"
        return out


def setup():
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [7.5, z]}
               for u, n, z in (("v", "VILLAGER_MALE", 7.5), ("m", "MAN_AT_ARMS", 8.5), ("a", "ARCHER", 9.5))]
    server = Server({u: {"Pos": (7.5, 64.0, z)} for u, z in (("v", 7.5), ("m", 8.5), ("a", 9.5))})
    return server, gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()


def test_the_bar_is_hidden_at_the_start():
    server, g = setup()
    assert "bossbar add aoe2mc:sel_p1 \"\"" in server.log and server.log[-1] != "bossbar set aoe2mc:sel_p1 visible true"
    assert "bossbar set aoe2mc:sel_p1 visible false" in server.log and g.bar is None


def test_a_selected_unit_shows_its_name_and_hit_points():
    server, g = setup()
    del server.log[:]
    g.select("v")
    assert server.log[-5:] == ['bossbar set aoe2mc:sel_p1 name [{"translate": "aoe2mc.unit.VILLAGER_MALE", "fallback": "Villager"}]', "bossbar set aoe2mc:sel_p1 players @a",
                               "execute store result bossbar aoe2mc:sel_p1 max run attribute v minecraft:max_health get",
                               "execute store result bossbar aoe2mc:sel_p1 value run data get entity v Health",
                               "bossbar set aoe2mc:sel_p1 visible true"]


def test_more_military_units_show_the_last_one_and_the_number():
    server, g = setup()
    g.select("m")
    g.select("a")
    assert g.bar == "a" and 'bossbar set aoe2mc:sel_p1 name [{"translate": "aoe2mc.unit.ARCHER", "fallback": "Archer"}, " (2)"]' in server.log


@pytest.mark.parametrize("steps", [1, 4])
def test_each_step_copies_the_health(steps):
    server, g = setup()
    g.select("m")
    del server.log[:]
    for _ in range(steps):
        g.step()
    assert server.log.count("execute store result bossbar aoe2mc:sel_p1 value run data get entity m Health") == steps


def test_a_dead_unit_hides_the_bar():
    server, g = setup()
    g.select("m")
    del server.entities["m"]
    g.step()
    assert g.bar is None and server.log[-1] == "bossbar set aoe2mc:sel_p1 visible false"
    del server.log[:]
    g.step()
    assert not any("bossbar" in c for c in server.log)                # no commands without a unit


def test_a_unit_at_0_health_hides_the_bar():
    server, g = setup()
    g.select("m")
    server.entities["m"]["Health"] = 0.0                               # dead: the body stays for 20 ticks
    g.step()
    assert g.bar is None and server.log[-1] == "bossbar set aoe2mc:sel_p1 visible false"


def test_no_selection_sends_no_bar_commands():
    server, g = setup()
    del server.log[:]
    g.step()
    assert not any("bossbar" in c for c in server.log)
    bossbar.show(g, None)
    assert server.log[-1] == "bossbar set aoe2mc:sel_p1 visible false"


@pytest.mark.mc
def test_the_bar_follows_the_health_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json

    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import combat, run
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=8.5, y=8.5)
    src = str(tmp_path / "bar.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data).setup()
        uuid, = g.soldiers
        g.select(uuid)
        hp = combat.stats("MILITIA").hp                                   # the AoE2 hit points of a militia
        assert str(hp) in game.command("bossbar get aoe2mc:sel_p1 max")
        assert str(hp) in game.command("bossbar get aoe2mc:sel_p1 value")
        assert "is currently visible" in game.command("bossbar get aoe2mc:sel_p1 visible")
        game.command(f"damage {uuid} 15")
        g.step()
        assert str(hp - 15) in game.command("bossbar get aoe2mc:sel_p1 value")
        game.command(f"kill {uuid}")
        g.step()
        assert g.bar is None and "is currently hidden" in game.command("bossbar get aoe2mc:sel_p1 visible")
