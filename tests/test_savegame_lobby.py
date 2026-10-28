"""A saved game keeps the later lobby settings (#2409, epic #2263): the population limit, the ending age, the game mode
and the treaty, and the treaty goes on with the time that passed before the save."""
from test_bot_attack import armed
from test_savegame_settings import main

from game import savegame, treaty

LOBBY = ["--pop-limit", "100", "--end-age", "castle", "--mode", "regicide", "--treaty", "10:00"]


def test_a_save_and_a_load_keep_the_lobby_settings(tmp_path, monkeypatch):
    first, saves = main(tmp_path, monkeypatch, LOBBY)
    calls, _ = main(tmp_path, monkeypatch, ["--load", str(tmp_path / "saves" / saves[0])], save=False)
    assert (calls["pop_limit"], calls["end_age"], calls["mode"], calls["treaty"]) == (100, "castle", "regicide", "10:00")
    assert {k: v for k, v in calls.items() if k != "state"} == {k: v for k, v in first.items() if k != "state"}


def test_an_option_given_with_load_wins_over_the_saved_lobby_setting(tmp_path, monkeypatch):
    _, saves = main(tmp_path, monkeypatch, LOBBY)
    calls, _ = main(tmp_path, monkeypatch, ["--load", str(tmp_path / "saves" / saves[0]), "--pop-limit", "150",
                                            "--mode", "standard"], save=False)
    assert (calls["pop_limit"], calls["mode"], calls["end_age"]) == (150, "standard", "castle")


def test_a_treaty_that_ran_2_minutes_of_10_goes_on_at_2_minutes():
    server, me, b = armed()
    treaty.start(me, 600.0)
    treaty.tick(me, 120.0)
    state = savegame.dump(me)
    assert state["treaty_time"] == 120.0
    server, me, b = armed()                                            # the loaded game: run.play starts the treaty
    treaty.start(me, 600.0, state["treaty_time"])
    assert me.game.treaty_time == 120.0 and treaty.holds(me)
    treaty.tick(me, 479.0)
    assert treaty.holds(me)
    treaty.tick(me, 1.0)
    assert not treaty.holds(me)                                        # 10:00 in all, not 12:00


def test_a_treaty_that_ended_before_the_save_does_not_start_again():
    server, me, b = armed()
    me.paper = True
    start = len(server.log)
    treaty.start(me, 600.0, 700.0)
    assert not treaty.holds(me)
    assert not any(c.startswith("aoe neutral") or "Treaty:" in c for c in server.log[start:])   # no truce, no chat line
