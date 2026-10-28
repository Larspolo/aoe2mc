"""The Gather of a second person (--people 2) finds the Gathers of all sides with build.sides, as the Gather of player 1
does (#3106): the receiver of a tribute, torpedo<n>, the Faith and Heresy of a bot, the allied sites of a repair."""
from test_cheat_end import game

from game import cheats, diplomacy, gather, monk, repair, run


def three():
    """Player 1 steps the Sides of person 2 and of the bot of player 3 (run.play); 1 and 2 are allied."""
    server, g1 = game()
    g1.players = {"0": {}, "1": {"team": 1}, "2": {"team": 1}, "3": {"team": 2}}
    g2 = gather.Gather.__new__(gather.Gather)
    g2.player, g2.players, g2.peers, g2.command = 2, g1.players, [g1], server.command
    g2.sites, g2.queues, g2.techs, g2.data, g2.map, g2.stock = [], {}, set(), g1.data, g1.map, dict(g1.stock)
    g3 = gather.Gather.__new__(gather.Gather)
    g3.player, g3.players, g3.share, g3.command, g3.map = 3, g1.players, g1, server.command, g1.map
    g3.sites, g3.queues, g3.techs = [{"name": "HOUSE", "player": 3, "footprint": [16, 18, 16, 18]}], {"tc": ["VILLAGER_MALE"]}, {"FAITH", "HERESY"}
    g1.bots = [run.Side(g2), run.Side(g3)]
    g1.sites.append({"name": "HOUSE", "player": 1, "footprint": [4, 6, 4, 6], "done": True})
    return server, g1, g2, g3


def test_a_tribute_of_person_2_finds_player_1():
    _, g1, g2, _ = three()
    assert diplomacy.receiver(g2, 1) is g1 and diplomacy.receiver(g2, 3).player == 3


def test_torpedo_of_person_2_stops_the_bot_of_player_3():
    _, g1, g2, g3 = three()
    cheats.ruin(g2, 3)
    assert [b.g.player for b in g1.bots] == [2] and not g3.sites and not g3.queues


def test_person_2_sees_the_faith_and_heresy_of_the_bot_and_the_allied_sites():
    _, g1, g2, _ = three()
    assert monk.heresy(g2, 3) and monk.heresy(g1, 3)
    assert monk.resist(g2, "s-3") == monk.resist(g1, "s-3") > 0
    assert (4, 6, 4, 6) in repair.owners(g2) and (4, 6, 4, 6) in repair.owners(g1)
