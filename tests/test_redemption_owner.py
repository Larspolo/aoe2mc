"""A building that a monk converts with Redemption belongs to its new owner on all sides (#2994, epic #2991): the new
owner trains in it, and the old owner does not and can attack it. A bot of player 2 builds the barracks (a done site)
or the map has it (an aoe2mc.json object)."""
from test_gather import FakeServer, grid

from game import bot, build, combat, gather, monk, train

BARRACKS = {"kind": "building", "name": "BARRACKS", "player": 2, "footprint": [10, 10, 13, 13]}
SITE = {"name": "BARRACKS", "player": 2, "footprint": (14, 16, 4, 6), "done": True, "progress": 1.0}


def setup(building=None):
    """A flat 40 × 40 map (tile size 1): a monk of player 1 at block (5.5, 5.5), the building of the map, and a bot of
    player 2 that shares the game of player 1."""
    objects = [{"kind": "unit", "name": "MONK", "player": 1, "uuid": "monk", "tile": [5.5, 5.5]}]
    if building:
        objects.append(dict(building))
    server = FakeServer({"monk": {"Pos": (5.5, 64.0, 5.5)}})
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.bots = [bot.Bot(server, g.data, player=2, share=g).setup()]
    return server, g


def convert(server, g, uuid):
    """Redemption: the monk converts the building uuid, a quarter second at a time (AoE2 seconds, at most 40)."""
    g.techs.add("REDEMPTION")
    g.chance.seed(1)
    server.entities[uuid] = {"Pos": (15.0, 64.0, 5.0)}
    server.entities["monk"]["Pos"] = (g.forts[uuid][0] - 0.5, 64.0, g.forts[uuid][2] + 0.5)
    assert monk.convert_order(g, {"monk"}, uuid)
    t = 0.0
    while uuid in g.forts and t < 40:
        monk.convert(g, 0.25)
        t += 0.25
    assert uuid not in g.forts


def test_a_monk_converts_a_barracks_that_the_bot_built():
    server, g = setup()
    b = g.bots[0]
    b.g.sites.append(dict(SITE))
    build.target(b.g, dict(SITE))
    uuid = combat.target_uuid([14, 4, 16, 6])
    assert (14, 16, 4, 6) in train.homes(b.g) and (14, 16, 4, 6) not in train.homes(g)
    convert(server, g, uuid)
    assert (14, 16, 4, 6) in train.homes(g) and (14, 16, 4, 6) not in train.homes(b.g)
    assert uuid in b.g.forts and uuid not in g.forts
    assert g.fort_players[uuid] == 1 and b.g.fort_players[uuid] == 1


def test_a_monk_converts_a_barracks_of_the_map_and_the_bot_can_attack_it():
    server, g = setup(BARRACKS)
    b = g.bots[0]
    uuid = combat.target_uuid(BARRACKS["footprint"])
    assert uuid not in b.g.forts
    convert(server, g, uuid)
    assert uuid in b.g.forts and b.g.fort_players[uuid] == 1 and g.fort_players[uuid] == 1
