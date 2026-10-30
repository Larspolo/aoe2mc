"""A building shoots the arrows of its garrison also after an earlier garrison came out of another building (#1285).
The check #1204 measured 0 damage: an enemy chased the villagers into the passage under the town center (#865), the
town center shot at that nearest enemy, and its arrows from above hit the own roof."""
import contextlib
import io
import json
import time

import pytest

from game import combat, garrison, gather


@pytest.mark.mc
def test_the_town_center_shoots_after_a_garrison_came_out_of_a_tower(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import run
    scn = scenarios.new_scenario(48)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=10, y=10)
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.WATCH_TOWER.ID, x=24, y=10)
    for k in range(3):
        um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=17.5 + k, y=16.5)
    um.add_unit(scenarios.PlayerId.TWO, UnitInfo.MILITIA.ID, x=10.5, y=15.5)   # 3 tiles south of the town center
    um.add_unit(scenarios.PlayerId.TWO, UnitInfo.MILITIA.ID, x=24.5, y=15.5)   # it chases the villagers
    src = str(tmp_path / "g.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    foe, chaser = [o["uuid"] for o in sorted((o for o in data["objects"] if o["kind"] == "unit" and o["player"] == 2),
                                             key=lambda o: o["tile"][0])]
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        combat.setup(game, data)
        tc, = [r for r, o in garrison.holders(g).items() if o["name"] == "TOWN_CENTER"]
        tower, = [r for r, o in garrison.holders(g).items() if o["name"] == "WATCH_TOWER"]
        for u in (foe, chaser):
            game.command(f"attribute {u} minecraft:max_health base set 1000")
            game.command(f"data modify entity {u} Health set value 1000f")
        game.command(f"data merge entity {foe} {{NoAI:1b}}")

        def health():
            return sum(float(game.command(f"data get entity {u} Health").rsplit(":", 1)[-1].strip().rstrip("f"))
                       for u in (foe, chaser))

        def walk(rect, seconds=60):
            g.choose(set(g.villagers), min(g.villagers))
            assert garrison.order(g, "nobody", (rect[0] + 1, rect[2] + 1)) == rect
            end = time.time() + seconds
            while len(g.garrisons.get(rect, [])) < 3 or g.entering:
                assert time.time() < end, (g.entering, g.garrisons)
                g.step()
                time.sleep(g.tick)

        walk(tower)
        garrison.out(g, tower)
        for _ in range(10):
            g.step()
            time.sleep(g.tick)
        walk(tc)
        for _ in range(10):                                            # the chaser comes after the villagers
            g.step()
            time.sleep(g.tick)
        h, end = health(), time.time() + 8
        while time.time() < end:
            g.step()
            time.sleep(g.tick)
        assert health() < h - 8, ("3 arrows of 4 damage, about each 1.2 s", g.positions([foe, chaser]))
