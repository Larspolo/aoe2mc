"""A saved game keeps the lobby settings Turbo Mode and the starting resources (#2359, #2264): `--load SAVE` alone
goes on with them, an infinite stock stays infinite, and each setting of run.py is either saved or has its reason."""
from test_bot_gather import bot_map
from test_savegame_settings import main

from game import gather, run, savegame


def saved(tmp_path, monkeypatch, argv):
    """Play with argv, save the game and return the path of the save."""
    _, saves = main(tmp_path, monkeypatch, argv)
    return str(tmp_path / "saves" / saves[0])


def test_load_alone_keeps_turbo_and_the_infinite_stock(tmp_path, monkeypatch):
    path = saved(tmp_path, monkeypatch, ["--turbo", "--resources", "infinite"])
    calls, _ = main(tmp_path, monkeypatch, ["--load", path], save=False)
    assert calls["turbo"] is True and calls["resources"] == "infinite"


def test_the_loaded_stock_stays_infinite(tmp_path, monkeypatch):
    path = saved(tmp_path, monkeypatch, ["--resources", "infinite"])
    server, me, b = bot_map()
    me.stock = gather.Endless(me.stock)                                 # the stock of a new Gather with "infinite"
    savegame.load(me, savegame.read(path))
    assert isinstance(me.stock, gather.Endless)


def test_an_option_given_with_load_wins_over_the_saved_resources(tmp_path, monkeypatch):
    path = saved(tmp_path, monkeypatch, ["--turbo", "--resources", "infinite"])
    calls, _ = main(tmp_path, monkeypatch, ["--load", path, "--resources", "standard"], save=False)
    assert calls["resources"] == "standard" and calls["turbo"] is True


def test_each_setting_is_saved_or_has_its_reason():
    """A new lobby setting fails here until it is in savegame.SETTINGS (saved) or in this list (not saved)."""
    not_saved = {"age": "the saved technologies hold the age, and play() starts no age in a loaded game",
                 "balance": "the saved teams hold the split of the ratings (#5168): a loaded game keeps them",
                 "ai": "the paths of the AI script files; the player names them again, the rules hold no state",
                 "record": "the player names a record file for each run, a saved path would write over it"}
    assert set(run.SETTINGS) - set(savegame.SETTINGS) == set(not_saved)
