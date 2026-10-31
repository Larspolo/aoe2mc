"""game/bot.py: an allied bot helps by taunts 48 (to the town center of the ally) and 51 (with the army of the ally),
#4892, on the map of test_bot_gather (the bot is player 2, the person is player 1)."""
from test_bot_gather import bot_map

from game.bot import build  # noqa: F401  (puts game/ on the path for the plain names)


def setup(team=1):
    server, me, b = bot_map()
    b.g.players.setdefault("1", {})["team"] = team
    b.g.players.setdefault("2", {})["team"] = 1
    if team == 1:
        b.g.enemies.pop("p1", None)                          # an ally is no enemy (owners.add after a team change)
    b.g.soldiers["s1"] = "MAN_AT_ARMS"
    server.entities["s1"] = {"Pos": (21.5, 64.0, 25.5), "Rotation": (0.0, 0.0)}
    sent = []
    command = server.command
    server.command = lambda c: sent.append(c) or command(c)
    return server, me, b, sent


def look(me, b, n, sent):
    me.taunted = [*getattr(me, "taunted", []), str(n)]
    b.give()
    sent.clear()
    b.time += 10
    b.assist()
    return [c for c in sent if c.startswith("aoe moveto s1")]


def test_taunt_48_sends_the_soldiers_to_the_town_center_of_the_ally():
    server, me, b, sent = setup()
    assert look(me, b, 48, sent) == ["aoe moveto s1 4 64 4"]


def test_taunt_51_follows_the_soldiers_of_the_ally():
    server, me, b, sent = setup()
    me.soldiers["a1"] = "MAN_AT_ARMS"
    server.entities["a1"] = {"Pos": (9.5, 64.0, 12.5), "Rotation": (0.0, 0.0)}
    assert look(me, b, 51, sent) == ["aoe moveto s1 9 64 12"]
    server.entities["a1"]["Pos"] = (14.5, 64.0, 3.5)
    b.time += 10
    sent.clear()
    b.assist()
    assert "aoe moveto s1 14 64 3" in sent
    assert look(me, b, 45, sent) == [] and b.helping is None   # a retreat ends the help


def test_an_enemy_taunt_changes_nothing():
    server, me, b, sent = setup(team=2)
    assert look(me, b, 48, sent) == [] and b.helping is None
