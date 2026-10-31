"""game/monk.py: all sides of a game share one list of the relics (#3116), so each relic exists once: a monk of
player 2 cannot pick up the relic that a monk of player 1 carries, and a relic in a monastery of player 1 is only of
player 1 (gold, the fallen monastery, the Lithuanian relic attack). Fake server."""
import json

from test_gather import grid
from test_monk_heal import HealServer

from game import bot, combat, gather, monk, run, savegame, train

HOME = (14, 18, 2, 6)                                                  # the monastery of player 1: x0, x1, z0, z1


def two_people():
    """A flat 24 × 24 map (tile size 1): a monk of each player, a relic at block (10, 5), a monastery of each player.
    The Gathers of players 1 and 2 share the relics as run.play joins them."""
    objects = [{"kind": "unit", "name": "MONK", "player": 1, "uuid": "m1", "tile": [5.5, 5.5]},
               {"kind": "unit", "name": "MONK", "player": 2, "uuid": "m2", "tile": [5.5, 9.5]},
               {"kind": "other", "name": "RELIC", "player": 0, "tile": [10.5, 5.5]},
               {"kind": "building", "name": "MONASTERY", "player": 1, "footprint": [14, 2, 18, 6]},
               {"kind": "building", "name": "MONASTERY", "player": 2, "footprint": [14, 14, 18, 18]}]
    server = HealServer({u: {"Pos": (5.5, 64.0, z), "Health": 30.0, "Max": 30.0} for u, z in (("m1", 5.5), ("m2", 9.5))})
    data = grid([[64] * 24 for _ in range(24)], objects)
    g1 = gather.Gather(server, data).setup()
    g2 = gather.Gather(server, data, player=2).setup()
    g1.bots, g2.peers = [run.Side(g2)], [g1, g2]
    g2.relics = g1.relics                                              # as run.play
    for g, m in ((g1, "m1"), (g2, "m2")):
        g.paper = True
        g.choose({m}, m)
    return server, g1, g2


def walk(server, g, m, x, z):
    """Monk m stands at block (x, z); one relic pass of g."""
    server.entities[m]["Pos"] = (x, 64.0, z)
    monk.relic_tick(g, monk.EVERY)


def test_a_monk_of_player_2_cannot_pick_up_the_relic_of_player_1():
    server, g1, g2 = two_people()
    assert monk.order(g1, "Steve", (10, 6))
    walk(server, g1, "m1", 10.5, 6.5)
    assert g1.relics == [{"at": None, "monk": "m1", "home": None, "player": 1}]
    assert not monk.order(g2, "Alex", (10, 6))                         # the relic is gone from its cell
    walk(server, g2, "m2", 10.5, 6.5)
    assert monk.carriers(g1) == {"m1": 0} and monk.carriers(g2) == {}
    assert len([c for c in server.log if c.startswith("execute") and "aoe_relic_0" in c]) == 1


def test_a_relic_in_the_monastery_of_player_1_is_only_of_player_1():
    server, g1, g2 = two_people()
    g1.data["players"] = {"1": {"civ": "LITHUANIANS"}, "2": {"civ": "LITHUANIANS"}}
    g1.relics[0].update(at=None, home=HOME, player=1)
    gold = g1.stock["gold"], g2.stock["gold"]
    for _ in range(60):
        monk.relic_tick(g1, monk.EVERY)
        monk.relic_tick(g2, monk.EVERY)
    assert g1.stock["gold"] > gold[0] and g2.stock["gold"] == gold[1]
    assert g1.relics[0]["home"] == HOME                                # player 2 has no such monastery: it stays in
    assert not [c for c in server.log if "decorated_pot keep" in c]
    assert train.stats(g1, "KNIGHT").attack > combat.stats("KNIGHT").attack       # the relic attack of player 1 only
    assert train.stats(g2, "KNIGHT").attack == combat.stats("KNIGHT").attack


def test_the_bot_shares_the_relics_of_player_1():
    _, g1, _ = two_people()
    assert bot.Bot(g1.game, g1.data, player=2, share=g1).g.relics is g1.relics


def test_a_loaded_game_of_two_people_keeps_one_relic_list():
    server, g1, g2 = two_people()
    g1.relics[0].update(at=None, home=HOME, player=1)
    d = json.loads(json.dumps(savegame.dump(g1), sort_keys=True))
    _, h1, h2 = two_people()
    savegame.load(h1, d)
    assert h2.relics is h1.relics and h1.relics == [{"at": None, "monk": None, "home": HOME, "player": 1}]


def test_a_save_before_3116_gives_each_relic_to_its_holder():
    server, g1, g2 = two_people()
    d = json.loads(json.dumps(savegame.dump(g1), sort_keys=True))
    d["players"]["1"]["relics"] = [{"at": None, "monk": None, "home": {"tuple": list(HOME)}}]    # one list each
    d["players"]["2"]["relics"] = [{"at": [10, 5], "monk": None, "home": None}]
    _, h1, h2 = two_people()
    savegame.load(h1, d)
    assert h2.relics is h1.relics and h1.relics == [{"at": None, "monk": None, "home": HOME, "player": 1}]
