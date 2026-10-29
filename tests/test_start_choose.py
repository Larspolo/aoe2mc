"""A person who takes another side in the lobby menu goes to the start view of the new player (#3350): `tp` and
`spawnpoint` of the new side, nothing for the own side or for a taken side."""
from game import run

STARTS = {1: (10, 64, 20), 2: (90, 66, 80)}


def make_game(starts=STARTS):
    g = run.Game.__new__(run.Game)
    g.people, g.sides, g.kind, g.spectators, sent = 2, {}, "vanilla", frozenset(), []
    g.starts, g.yaw = starts, 45.0
    g.command = sent.append
    return g, sent


def moves(sent):
    return [c for c in sent if c.startswith(("tp ", "spawnpoint "))]


def test_a_choice_of_player_2_moves_the_person_to_its_start():
    g, sent = make_game()
    g.side("Alex")                                    # player 1
    sent.clear()
    assert g.choose("Alex", 2)
    assert moves(sent) == ["tp Alex 90.5 66 80.5 45.0 0", "spawnpoint Alex 90 66 80 45.0 0"]


def test_a_choice_of_the_own_side_sends_no_move():
    g, sent = make_game()
    g.side("Alex")
    sent.clear()
    assert g.choose("Alex", 1)
    assert moves(sent) == []


def test_a_taken_side_sends_no_move():
    g, sent = make_game()
    g.side("Alex")
    g.side("Steve")                                   # player 2
    sent.clear()
    assert not g.choose("Alex", 2)
    assert moves(sent) == [] and g.sides["Alex"] == 1


def test_a_world_without_a_start_sends_no_move():
    g, sent = make_game(starts={})
    g.side("Alex")
    sent.clear()
    assert g.choose("Alex", 2)
    assert moves(sent) == []
