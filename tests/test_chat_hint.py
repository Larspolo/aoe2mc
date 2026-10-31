"""A person who joins a side of a game of two or more people gets the chat targets in the chat (#3555).
A spectator and a single player do not get it: they have no team to chat to."""
import json

from game import run


def make_game(people):
    g = run.Game.__new__(run.Game)
    g.people, g.sides, g.kind, g.spectators, sent = people, {}, "vanilla", frozenset(), []
    g.command = sent.append
    return g, sent


def test_a_person_on_a_side_gets_the_chat_hint_in_a_game_of_two():
    g, sent = make_game(2)
    g.side("Alex")
    assert sent == ["team join p1 Alex", 'tellraw Alex ' + json.dumps(run.lang.text(run.CHAT_HINT_KEY, color="gray"))]


def test_a_single_player_gets_no_chat_hint():
    g, sent = make_game(1)
    g.side("Alex")
    assert not any("tellraw" in c for c in sent)


def test_a_spectator_gets_no_chat_hint():
    g, sent = make_game(2)
    g.side("Alex")
    g.side("Steve")
    del sent[:]
    g.side("Pat")                                     # the third person of a game of two: a spectator
    assert g.spectators == {"Pat"}
    assert not any("tellraw" in c for c in sent)


def test_the_hint_names_the_chat_targets():
    assert run.CHAT_HINT.count("/") == 2 and "/tm" in run.CHAT_HINT and "/msg" in run.CHAT_HINT
