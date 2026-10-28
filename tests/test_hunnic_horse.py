"""#2466, epic #1088: on a Nomad start the first town center of a Hun player spawns a Hunnic Horse (AoE2 DE wiki,
Huns), a tamed Minecraft horse of the player in front of it. Fake server of test_civ_town_center."""
import math

from test_civ_town_center import TC, UNITS, game

from game import build


def horses(civ, objects):
    server, g = game(civ, objects)
    g.stock.update(wood=1000, stone=1000)
    build.rise(g, build.found(g, "TOWN_CENTER", (6, 10, 6, 10)), math.inf)
    build.rise(g, build.found(g, "TOWN_CENTER", (0, 4, 10, 14)), math.inf)   # a second one spawns none
    return [c for c in server.log if c.startswith("summon minecraft:horse")]


def test_a_hun_nomad_gets_a_tamed_horse_in_front_of_its_first_town_center():
    out = horses("HUNS", UNITS)
    assert len(out) == 1 and "Tame:1b" in out[0] and '"aoe2mc.p1"' in out[0] and "Hunnic Horse" in out[0]
    x, _, z = map(float, out[0].split()[2:5])
    assert 5 <= x <= 11 and 5 <= z <= 11                               # next to the footprint (6, 10, 6, 10)


def test_a_hun_with_a_town_center_and_a_britons_nomad_get_no_horse():
    assert horses("HUNS", UNITS + [TC]) == [] and horses("BRITONS", UNITS) == []
