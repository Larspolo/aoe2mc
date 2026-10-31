"""A ship finds a Gaia unit, a Gaia ship joins with its crew, and a Gaia unit inside a building or a ship stays Gaia
(#5146). The fake RCON of tests/test_gaia_units.py."""
import test_gaia_units as t
from test_gaia_units import GAIA, MILITIA, VILL, gaia, game


def test_a_ship_of_player_1_near_a_gaia_unit_gives_it_to_player_1():
    g, _, pos, objects = game()
    ship = "00000000-0000-0000-0000-0000000000b1"
    g.villagers = {}
    g.soldiers[ship] = "GALLEY"
    g.ships[ship] = object()
    pos.pop(VILL)
    pos[ship] = (10 * t.T + (gaia.RANGE - 1) * t.T, 62.0, 10 * t.T)
    gaia.tick(g)
    assert objects[0]["player"] == 1 and g.soldiers[GAIA] == "MILITIA"


def test_a_gaia_ship_near_a_unit_of_player_1_joins_with_its_crew():
    g, _, _, objects = game(objects=[{"kind": "unit", "name": "GALLEY", "player": 0, "uuid": GAIA, "tile": [10.5, 10.0]}])
    gaia.tick(g)
    assert objects[0]["player"] == 1 and g.soldiers[GAIA] == "GALLEY"
    crew = f"execute as {GAIA} on passengers run "
    assert f"{crew}tag @s add aoe2mc.p1" in g.sent and f"{crew}team join p1 @s" in g.sent
    assert f"team join p1 {GAIA}" in g.sent


def test_a_gaia_unit_inside_a_building_or_a_ship_stays_gaia():
    for holder in (7, 9):                                            # the reference ID of a building or a ship
        g, b, _, objects = game(holder=holder)
        gaia.tick(g)
        assert objects[0]["player"] == 0 and not g.sent and GAIA not in g.soldiers and MILITIA in b.soldiers
