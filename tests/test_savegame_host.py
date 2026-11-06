"""A saved network game keeps its network options (#5923, epic #5890): `--load SAVE` alone opens the game to the network
again with the same address, port, white-list and login check, and an option given with `--load` wins."""
import argparse

from game import savegame

NETWORK = {"host": True, "invite": "Alex,Sam", "offline": True, "address": "203.0.113.7", "port": 25600}


def saved(a):
    """The settings of a game as run.main saves them: game.settings = {k: getattr(a, k) for k in savegame.SETTINGS}."""
    return {"settings": {k: getattr(a, k) for k in savegame.SETTINGS if hasattr(a, k)}}


def test_a_save_of_a_network_game_gives_the_network_options_back_with_load():
    a = argparse.Namespace(host=True, invite="Alex,Sam", offline=True, address="203.0.113.7", port=25600)
    b = argparse.Namespace(host=False, invite=None, offline=False, address=None, port=None)
    savegame.settings(b, saved(a), given=())
    assert (b.host, b.invite, b.offline, b.address, b.port) == (True, "Alex,Sam", True, "203.0.113.7", 25600)


def test_an_invite_given_with_load_wins_over_the_saved_names():
    b = argparse.Namespace(host=False, invite="Alex,Sam,Robin", offline=False, address=None, port=None)
    savegame.settings(b, saved(argparse.Namespace(**NETWORK)), given=("invite",))
    assert b.invite == "Alex,Sam,Robin"
    assert (b.host, b.address, b.port) == (True, "203.0.113.7", 25600)
