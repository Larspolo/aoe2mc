"""game/savegame.py and game/build.py: the buildings of a save work again after a load (#2980). A farm has its feet and
its farmer works on it, a lumber camp is a wood drop site and blocks its cells, a construction site blocks its footprint,
and a house is a fort of its sides. The load sends no command again and gives no one-time gift. Fake server, no Minecraft."""
import json

from test_gather import FakeServer, grid

from game import build, combat, gather, savegame

FARM, CAMP, SITE, HOUSE = (40, 76, 40, 76), (100, 108, 100, 108), (120, 128, 120, 128), (40, 48, 120, 128)


def fresh():
    """A 200 × 200 block map of 4 blocks per tile, a mill and a villager of player 1 next to the farm."""
    objects = [{"kind": "building", "name": "MILL", "player": 1, "tile": [21, 21], "footprint": [84, 84, 88, 88]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [9.5, 9.5]}]
    data = grid([[64] * 200 for _ in range(200)], objects)                # the mill: the drop site of the food
    data.update(tile_size=4, level_height=1, players={"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}})
    server = FakeServer({"v": {"Pos": (38.5, 64.0, 38.5)}})
    return gather.Gather(server, data, start={}).setup(), server


def played():
    """A farm, a lumber camp and a house that are complete, and a construction site that is not."""
    g, _ = fresh()
    build.rise(g, build.found(g, "FARM", FARM, free=True), 1e6)
    build.rise(g, build.found(g, "LUMBER_CAMP", CAMP, free=True), 1e6)
    build.rise(g, build.found(g, "HOUSE", HOUSE, free=True), 1e6)
    build.found(g, "HOUSE", SITE, free=True)
    return g


def loaded(g):
    h, server = fresh()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return h, server


def food(server):
    return sum(int(c.split()[-1]) for c in server.log if c.startswith("scoreboard players add Food aoe_res"))


def test_a_farm_of_the_save_has_its_feet_after_a_load():
    h, _ = loaded(played())
    assert h.map.feet[(11, 11)] == FARM                                 # a farmer stands on it (#2980)
    assert h.map.spot((11, 11)) == {(x, z) for x in range(40, 76) for z in range(40, 76)}


def test_a_farmer_of_the_save_gathers_food_after_a_load():
    h, server = loaded(played())
    h.select("v")
    h.send((11, 11))
    for _ in range(20000):
        h.step()                                                        # a KeyError here: the farm had no feet
        if food(server) > 0:
            break
    assert food(server) > 0


def test_a_lumber_camp_is_a_drop_site_and_blocks_its_cells_after_a_load():
    h, _ = loaded(played())
    assert any((105, 105) in cells for cells in h.map.drops["wood"])
    assert not h.map.free(105, 105)


def test_a_construction_site_blocks_its_footprint_after_a_load():
    h, _ = loaded(played())
    assert not h.map.free(125, 125)


def test_a_house_of_the_save_is_a_fort_after_a_load():
    h, _ = loaded(played())
    assert h.fort_names.get(combat.target_uuid([40, 120, 48, 128])) == "HOUSE"


def test_the_load_sends_no_building_command_and_gives_no_gift_again():
    g = played()
    stock = dict(g.stock)
    h, server = loaded(g)
    assert h.stock == stock
    assert not [c for c in server.log if c.startswith(("setblock", "summon"))]
