"""#5341: each person hears the peace tracks of game/data/music.jsonl in turn, each after a stopsound of the music of
the client; a bot hears nothing, and the end of the game stops the music."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import cheats  # noqa: E402
import music  # noqa: E402
from test_scenario_mode import game  # noqa: E402


def setup():
    server, g, bot = game({"0": {}, "1": {}, "2": {}})
    bot.share = g                                                      # a bot: bot.Bot sets it
    now = [100.0]
    g.clock = lambda: now[0]
    return server, g, now


def played(server, start):
    return [c for c in server.log[start:] if "music" in c]


def test_the_tracks_play_in_turn_after_the_end_of_each():
    server, g, now = setup()
    first, second = music.PEACE[0], music.PEACE[1 % len(music.PEACE)]
    music.tick(g)
    assert played(server, 0) == ["stopsound @a[team=p1] music",
                                 f"playsound {first['name']} music @a[team=p1] ~ ~ ~ 1 1 1"]
    start = len(server.log)
    now[0] += first["seconds"] - 1
    music.tick(g)
    assert played(server, start) == []
    now[0] += 2
    music.tick(g)
    assert played(server, start) == ["stopsound @a[team=p1] music",
                                     f"playsound {second['name']} music @a[team=p1] ~ ~ ~ 1 1 1"]


def test_a_bot_gets_no_command():
    server, g, _ = setup()
    music.tick(g)
    assert not any("team=p2" in c for c in played(server, 0))


def test_the_end_of_the_game_stops_the_music():
    server, g, _ = setup()
    start = len(server.log)
    cheats.over(g, lambda n: n == 1)
    assert "stopsound @a music" in server.log[start:]
    music.tick(g)                                                      # no new track after the end
    assert not any(c.startswith("playsound") and "music" in c for c in server.log[start:])
