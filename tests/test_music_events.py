"""#5339: the team of a player hears a short tune at its age up, and each team its victory or defeat tune at the end of
the game (category music). The sounds come from game/data/tunes.jsonl."""
import cheats
from test_feudal_age import COST, SLOT, TIME, add
from test_loom import setup
from test_scenario_mode import game

from game import train


def tune(event, n):
    m = cheats.TUNES[event]
    return f"playsound minecraft:{m['sound']} music @a[team=p{n}] ~ ~ ~ 1 {m['pitch']} 1"


def test_an_age_up_plays_the_age_up_tune_to_the_own_team():
    server, g = setup(food=COST)
    add(g, "MINING_CAMP", "DOCK")
    rect = train.open_menu(g, "Steve", (3, 3))
    train.order(g, "Steve", rect, SLOT)
    train.tick(g, TIME)
    assert server.log.count(tune("age_up", 1)) == 1
    assert not any(c.startswith("playsound") and "@a " in c for c in server.log)


def test_the_end_plays_victory_to_the_winner_and_defeat_to_the_others():
    server, g, _ = game({"0": {}, "1": {}, "2": {}})
    start = len(server.log)
    cheats.over(g, lambda n: n == 1)
    log = server.log[start:]
    assert tune("victory", 1) in log and tune("defeat", 2) in log
    assert tune("defeat", 1) not in log and tune("victory", 2) not in log


def test_a_tune_uses_the_values_of_test_data(monkeypatch):
    server, g, _ = game({"0": {}, "1": {}})
    monkeypatch.setitem(cheats.TUNES, "defeat", {"name": "defeat", "sound": "x.y", "pitch": 0.5})
    cheats.tune(g, 3, "defeat")
    assert server.log[-1] == "playsound minecraft:x.y music @a[team=p3] ~ ~ ~ 1 0.5 1"


def test_the_music_stops_before_the_end_tune():
    server, g, _ = game({"0": {}, "1": {}})
    start = len(server.log)
    cheats.over(g, lambda n: n == 1)
    log = server.log[start:]
    assert log.index("stopsound @a music") < log.index(tune("victory", 1))
