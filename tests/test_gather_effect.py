"""game/gather.py: each gather step shows a work effect at the resource (#592)."""
from test_gather import FakeServer, grid

from game import gather


def setup(objects):
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}] + objects
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    return server, gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), carry=3, chop=0.25).setup()


def first_work(server, g, tile):
    g.select("v")
    g.send(tile)
    for _ in range(200):
        n = len(server.log)
        g.step()
        if g.villagers["v"].load:
            return server.log[n:]


def test_one_gather_step_turns_the_villager_and_plays_particles_and_a_sound():
    server, g = setup([{"kind": "other", "name": "TREE_PINE", "tile": [12.5, 7.5]}])
    log = first_work(server, g, (12, 7))
    work = [c for c in log if c.split()[0] in ("rotate", "particle", "playsound")]
    x, y, z = g.villagers["v"].pos
    assert x == 11.5 and z == 7.5                                      # next to the tree, on its west side
    assert work == ["rotate v facing 12.50 65.00 7.50",
                    'particle minecraft:block{block_state:{id:"minecraft:spruce_log"}} 12.50 65.00 7.50 0.2 0.2 0.2 0 8',
                    "playsound minecraft:block.wood.hit block @a 12.50 65.00 7.50 1 1.1"]


def test_each_resource_has_its_block_and_sound():
    for obj, tile, block, sound in [
            ({"kind": "other", "name": "FORAGE_BUSH", "tile": [12.5, 7.5]}, (12, 7),
             '{id:"minecraft:sweet_berry_bush",Properties:{age:"3"}}', "block.sweet_berry_bush.pick_berries"),
            ({"kind": "other", "name": "GOLD_MINE", "tile": [12.5, 7.5]}, (12, 7), '{id:"minecraft:gold_ore"}',
             "block.stone.hit"),
            ({"kind": "other", "name": "STONE_MINE", "tile": [12.5, 7.5]}, (12, 7), '{id:"minecraft:stone"}',
             "block.stone.hit"),
            ({"kind": "building", "name": "FARM", "player": 1, "tile": [13.5, 8.5], "footprint": [12, 7, 15, 10]},
             (13, 8), '{id:"minecraft:wheat",Properties:{age:"7"}}', "item.hoe.till")]:
        server, g = setup([obj])
        log = first_work(server, g, tile)
        assert f"particle minecraft:block{{block_state:{block}}}" in " ".join(log), obj["name"]
        assert any(c.startswith(f"playsound minecraft:{sound} block @a") for c in log), obj["name"]
