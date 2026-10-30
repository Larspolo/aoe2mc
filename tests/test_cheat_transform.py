"""game/cheats.py: a transformation cheat turns each own unit of its kind into another unit (#967)."""
import re

import pytest
from test_gather import FakeServer, grid

from game import cheats, combat, gather

FROM = {"cameleon": "CAMEL_RIDER", "flemish reformation": "VILLAGER_MALE", "grab your pitchforks": "VILLAGER_MALE",
        "put on your capes": "MAN_AT_ARMS", "yes we khan": "MANGUDAI"}
TO = {c: e.to for c, e in cheats.CODES.items() if isinstance(e, cheats.Transform)}


class HurtServer(FakeServer):
    """A FakeServer whose entities can have Health and max_health."""

    def command(self, cmd):
        if m := re.fullmatch(r"data get entity (\S+) Health", cmd):
            self.log.append(cmd)
            return f"{m[1]} has the following entity data: {self.entities[m[1]]['Health']}f"
        if m := re.fullmatch(r"attribute (\S+) minecraft:max_health get", cmd):
            self.log.append(cmd)
            return f"Value of attribute Max Health for entity {m[1]} is {self.entities[m[1]]['Max']}"
        return super().command(cmd)


def setup(name, cheats_on=True):
    """A flat 24 × 24 map with unit `name` of player 1 (UUID "a"), the same unit of player 2 ("b"), and one archer
    of player 1 ("c") that no code turns."""
    objects = [{"kind": "unit", "name": name, "player": 1, "uuid": "a", "tile": [5.5, 5.5]},
               {"kind": "unit", "name": name, "player": 2, "uuid": "b", "tile": [15.5, 15.5]},
               {"kind": "unit", "name": "ARCHER", "player": 1, "uuid": "c", "tile": [8.5, 8.5]}]
    server = HurtServer({"a": {"Pos": (5.5, 64.0, 5.5), "Health": 20.0, "Max": 40.0},
                         "b": {"Pos": (15.5, 64.0, 15.5), "Health": 40.0, "Max": 40.0},
                         "c": {"Pos": (8.5, 64.0, 8.5), "Health": 30.0, "Max": 30.0}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), cheats=cheats_on).setup()
    return server, g


@pytest.mark.parametrize("code", sorted(TO))
def test_a_transformation_turns_the_own_units_only(code):
    server, g = setup(FROM[code])
    g.choose({"a", "c"})
    server.scores["aoe_cheat"] = cheats.NAMES.index(code) + 1
    assert cheats.clicks(g) == [("Steve", code)]
    summons = [c for c in server.log if c.startswith("summon ")]
    assert len(summons) == 1
    assert [float(v) for v in summons[0].split()[2:5]] == [5.5, 64.0, 5.5]   # at the place of the old unit
    assert "kill a" in server.log and "kill b" not in server.log and "kill c" not in server.log
    new = (set(g.soldiers) | set(g.villagers)) - {"c"}
    assert len(new) == 1 and "a" not in g.soldiers and "a" not in g.villagers
    uuid, = new
    assert g.soldiers.get(uuid, TO[code] if uuid in g.villagers else None) == TO[code]
    assert "a" not in {o.get("uuid") for o in g.units}
    assert g.selected == {"c"}                                         # the old unit left the selection
    hp = min(combat.stats(TO[code]).hp, 1024)
    assert f"data modify entity {uuid} Health set value {hp / 2:.1f}f" in server.log   # half of its hit points


def test_the_new_unit_has_its_aoe2_values():
    server, g = setup("VILLAGER_MALE")
    cheats.apply(g, "Steve", "grab your pitchforks")
    stats = next(c for c in server.log if c.startswith("aoe stats "))
    uuid = stats.split()[2]
    assert stats == combat.stats_command(uuid, TO["grab your pitchforks"])


def test_a_unit_with_full_health_keeps_the_full_health():
    server, g = setup(FROM["put on your capes"])
    server.entities["a"]["Health"] = 40.0
    cheats.apply(g, "Steve", "put on your capes")
    assert not any("Health set" in c for c in server.log)
    assert TO["put on your capes"] in g.soldiers.values() and "c" in g.soldiers


def test_no_transformation_with_cheats_off():
    server, g = setup("VILLAGER_MALE", cheats_on=False)
    server.scores["aoe_cheat"] = cheats.NAMES.index("grab your pitchforks") + 1
    assert cheats.clicks(g) == []
    assert not any(c.startswith(("summon ", "kill ")) for c in server.log)


@pytest.mark.mc
def test_pitchforks_turn_a_villager_into_a_militia_that_walks_on_a_server(tmp_path):
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
    from game import ai, run
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=6, y=6)
    src = str(tmp_path / "pitchforks.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, cheats=True).setup()
        old, = g.villagers
        cheats.apply(g, "nobody", "grab your pitchforks")
        militia, = g.soldiers
        assert g.soldiers[militia] == TO["grab your pitchforks"] and not g.villagers
        end = time.time() + 5                                          # a killed mob stays for its death animation
        while g.pos(old):
            assert time.time() < end, "the villager is gone"
            time.sleep(0.25)
        start = g.pos(militia)
        assert start, "the Flemish Militia exists"
        goal = (40.5, g.map.y(40, 40), 40.5)
        assert "Moved 1 units" in ai.move(game, militia, TO["grab your pitchforks"], g.map.T, *goal)
        end = time.time() + 60
        while (p := g.pos(militia)) and (p[0] - goal[0]) ** 2 + (p[2] - goal[2]) ** 2 > 2 ** 2:
            assert time.time() < end, f"the Flemish Militia is at {p}, not at {goal} (from {start})"
            time.sleep(0.5)
