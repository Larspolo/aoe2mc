"""game/savegame.py: a building that fell before the save stays gone after the load (#2985): no side has it in its
forts, its cells are walkable, and its ground is as before. A load does not give the loot again."""
import json

from test_fall_shared_target import house, two_sides
from test_wonder import targets

from game import combat, savegame

HOUSE = [15, 15, 17, 17]
CELL = (16, 16)


def razed_house(objects=None):
    """A house that player 1 razed, saved: (the save dict, the Gather of the raze, its uuid)."""
    server, g, g2 = two_sides(house() if objects is None else objects)
    g2.player = 2                                                      # the two sides are two players
    uuid = combat.target_uuid(HOUSE)
    g.sieged.add(uuid)
    targets(server, set())                                             # the plugin removed the house
    g.fall()
    return json.loads(json.dumps(savegame.dump(g))), g, uuid


def loaded(d):
    server, h, h2 = two_sides(house())                                 # the house is back on the map, as at a start
    h2.player = 2
    savegame.load(h, d)
    return h, h2


def test_a_razed_house_is_in_no_forts_after_a_load():
    d, _, uuid = razed_house()
    h, h2 = loaded(d)
    assert uuid not in h.forts and uuid not in h2.forts


def test_a_razed_house_frees_its_cells_after_a_load():
    d, g, _ = razed_house()
    h, _ = loaded(d)
    assert CELL not in h.map.blocked
    assert h.map.ground[16][16] == g.map.ground[16][16]
