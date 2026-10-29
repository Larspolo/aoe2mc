"""Each person of a game of more people starts at the start view of its own player (#3347): `tp` and `spawnpoint`
on the first join to a side, nothing on a join again, for a spectator or for a world without "start"."""
from game import run

STARTS = {1: (10, 64, 20), 2: (90, 66, 80)}


def make_game(people, starts=STARTS):
    g = run.Game.__new__(run.Game)
    g.people, g.sides, g.kind, g.spectators, sent = people, {}, "vanilla", frozenset(), []
    g.starts, g.yaw = starts, 45.0
    g.command = sent.append
    return g, sent


def moves(sent):
    return [c for c in sent if c.startswith(("tp ", "spawnpoint "))]


def test_each_person_goes_to_the_start_of_its_side():
    g, sent = make_game(2)
    g.side("Alex")
    g.side("Steve")
    assert moves(sent) == ["tp Alex 10.5 64 20.5 45.0 0", "spawnpoint Alex 10 64 20 45.0",
                           "tp Steve 90.5 66 80.5 45.0 0", "spawnpoint Steve 90 66 80 45.0"]


def test_a_join_again_keeps_the_place():
    g, sent = make_game(2)
    g.side("Alex")
    g.side("Steve")
    sent.clear()
    g.side("Steve")
    assert moves(sent) == [] and g.sides["Steve"] == 2


def test_a_spectator_and_an_old_world_do_not_move():
    g, sent = make_game(2)
    g.side("Alex")
    g.side("Steve")
    sent.clear()
    g.side("Pat")                                     # the third person of a game of two: a spectator
    assert moves(sent) == []
    g, sent = make_game(2, starts={})
    g.side("Alex")
    assert moves(sent) == []


def test_a_game_of_one_person_sends_nothing():
    g, sent = make_game(1)
    g.side("Alex")
    assert sent == []
