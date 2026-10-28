"""game/regen.py: Bengali ships regenerate 15 hit points per minute, Puru cavalry 25 from the Classical Age with no
enemy unit within 10 tiles, as in AoE2 DE (civs.REGEN, #2334)."""
import re

import pytest
from test_gather import grid
from test_monk_heal import HealServer
from test_regeneration import AGES, run

from game import gather


class CrewServer(HealServer):
    """A HealServer whose ship crew commands (`execute as <uuid> on passengers run ... @s ...`) run on the ship entity."""

    def command(self, cmd):
        if m := re.fullmatch(r"execute as (\S+) on passengers run (.*)", cmd):
            self.log.append(cmd)
            return super().command(m[2].replace("@s", m[1]))
        return super().command(cmd)


def setup(civ, age, *units):
    """A flat 32 × 32 map (tile size 1) with the units of `units` (uuid, name, player, x, health, max) at z 2.5: the own
    ships go to g.ships."""
    objects, ents = [], {}
    for uuid, name, player, x, hp, top in units:
        objects.append({"kind": "unit", "name": name, "player": player, "uuid": uuid, "tile": [x, 2.5]})
        ents[uuid] = {"Pos": (x, 64.0, 2.5), "Health": hp, "Max": top}
    server = CrewServer(ents)
    g = gather.Gather(server, grid([[64] * 32 for _ in range(32)], objects)).setup()
    g.data["players"] = {"1": {"civ": civ}, "2": {"civ": "FRANKS"}}
    g.techs.update(AGES[age])
    for uuid, name, player, *_ in units:
        if player == 1:
            g.soldiers[uuid] = name
            if name.endswith(("GALLEY", "SHIP")):
                g.ships[uuid] = gather.Villager(uuid, ents[uuid]["Pos"])
    return server, g


def test_a_bengali_ship_regenerates_15_hit_points_per_minute_up_to_its_maximum():
    server, g = setup("BENGALIS", 0, ("s", "GALLEY", 1, 2.5, 50.0, 90.0))
    run(g, 60)
    assert server.entities["s"]["Health"] == pytest.approx(65, abs=0.01)
    assert any(c.startswith("execute as s on passengers run data modify entity @s Health") for c in server.log)
    run(g, 240)
    assert server.entities["s"]["Health"] == 90.0


def test_a_ship_of_another_civilization_does_not_regenerate():
    server, g = setup("BRITONS", 3, ("s", "GALLEY", 1, 2.5, 50.0, 90.0))
    run(g, 60)
    assert server.entities["s"]["Health"] == 50.0


@pytest.mark.parametrize("age, gain", [(1, 0), (2, 25), (3, 25)])
def test_puru_cavalry_regenerates_25_hit_points_per_minute_from_the_classical_age(age, gain):
    server, g = setup("PURU", age, ("k", "KNIGHT", 1, 2.5, 50.0, 100.0), ("m", "MAN_AT_ARMS", 1, 3.5, 20.0, 45.0))
    run(g, 60)
    assert server.entities["k"]["Health"] == pytest.approx(50 + gain, abs=0.01)
    assert server.entities["m"]["Health"] == 20.0                     # not cavalry


@pytest.mark.parametrize("x, gain", [(12.0, 0), (13.0, 25)])
def test_puru_cavalry_does_not_regenerate_with_an_enemy_unit_within_10_tiles(x, gain):
    server, g = setup("PURU", 3, ("k", "KNIGHT", 1, 2.5, 50.0, 100.0), ("e", "MILITIA", 2, x, 40.0, 40.0))
    run(g, 60)
    assert server.entities["k"]["Health"] == pytest.approx(50 + gain, abs=0.01)
    assert server.entities["e"]["Health"] == 40.0
