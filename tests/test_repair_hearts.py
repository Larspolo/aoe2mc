"""game/repair.py: the hearts of a siege unit go up while villagers repair it (#1521). The repair sets the Health of the
crew with a command, which fires no Paper event, so it sends `aoe label` after each change, as the building repair."""
import pytest
from test_repair_siege import RAM, setup

from game import repair


def test_each_health_change_of_the_repair_updates_the_name_line():
    server, g = setup(hp=RAM - 35)
    assert repair.unit_order(g, "Steve", "ram")
    steps = 0
    while g.villagers["v0"].state != "idle" and steps < 5000:
        g.step()
        steps += 1
    assert server.health["ram"] == RAM
    sets = [i for i, c in enumerate(server.log) if c.startswith("execute as ram on passengers run data modify")]
    assert sets and all(server.log[i + 1] == "aoe label ram" for i in sets)


@pytest.mark.mc
def test_the_hearts_of_a_ram_go_up_during_the_repair_on_a_server(tmp_path):
    """A ram at 100 of 175 hit points with a name line (as after a hit) shows 3 red and 2 gray hearts; after the repair
    5 red hearts, and the name line is hidden again (not hurt, not selected)."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import time

    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import combat, gather, run
    scn = scenarios.new_scenario(24)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.BATTERING_RAM.ID, x=12.5, y=12.5)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=8.5, y=12.5)
    src = str(tmp_path / "r.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25, start={"wood": 100, "gold": 100}).setup()
        ram, = [u for u, n in g.soldiers.items() if n == "BATTERING_RAM"]

        def hearts():
            def part(i):
                out = game.command(repair.crew(ram) + f"data get entity @s CustomName.extra[{i}].text")
                assert "has the following entity data" in out, out
                return out.rsplit(":", 1)[1].count("❤")
            return part(2), part(3), game.command(repair.crew(ram) + "data get entity @s CustomNameVisible").rstrip().endswith("1b")
        game.command(repair.crew(ram) + "data modify entity @s Health set value 100.0f")
        assert game.command(combat.label_command(ram, "BATTERING_RAM")).strip() == "Label: 1 units"   # as after a hit
        assert hearts() == (3, 2, True)
        g.choose(set(g.villagers), min(g.villagers))
        assert repair.unit_order(g, "nobody", ram)
        end = time.time() + 120
        while repair.unit_hp(g, ram)[0] < RAM:
            assert time.time() < end, repair.unit_hp(g, ram)
            g.step()
            time.sleep(g.tick)
        assert hearts() == (5, 0, False)
