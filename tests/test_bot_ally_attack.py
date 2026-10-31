"""game/bot.py: the AI command taunts of an ally (#4828): 31 attack now, 36 wait, 61-68 attack player N, on the map of
test_bot_gather (the bot is player 2, the person is player 1)."""
from test_bot_gather import bot_map

from game.bot import build  # noqa: F401  (puts game/ on the path for the plain names)


def setup(monkeypatch, ally=True):
    server, me, b = bot_map()
    for p in ("1", "2", "3"):
        b.g.players.setdefault(p, {})
    if ally:
        b.g.players["1"]["team"] = b.g.players["2"]["team"] = 1
    fights, said = [], []
    monkeypatch.setattr(b, "fight", lambda: fights.append(b.time))
    command = b.g.command
    monkeypatch.setattr(b.g, "command", lambda c: (said.append(c) if c.startswith("tellraw") else None) or command(c))
    b.attack = 10 ** 6                                     # far after the test
    return me, b, fights, said


def taunt(me, n):
    me.taunted = [*getattr(me, "taunted", []), str(n)]   # as gather.Game.clicks keeps them (#4827)


def step(b):
    b.looked = -10 ** 6                                    # no wait between two looks
    b.orders()


def test_taunt_31_of_an_ally_attacks_now_and_36_waits(monkeypatch):
    me, b, fights, said = setup(monkeypatch)
    step(b)
    assert not fights
    taunt(me, 31)
    step(b)
    assert len(fights) == 1 and len(said) == 1          # one answer line (answer(), #4829)
    taunt(me, 36)
    b.attack = 0                                           # its own attack time is over: it still waits
    step(b)
    assert len(fights) == 1
    taunt(me, 31)
    step(b)
    assert len(fights) == 2


def test_taunt_31_of_an_enemy_does_nothing(monkeypatch):
    me, b, fights, said = setup(monkeypatch, ally=False)
    taunt(me, 31)
    step(b)
    assert not fights and not said


def test_taunt_63_sets_the_foe_to_an_enemy_only(monkeypatch):
    me, b, fights, said = setup(monkeypatch)
    taunt(me, 63)
    step(b)
    assert b.foe == 3 and fights
    b.foe = 1
    b.g.players["3"]["team"] = 1                           # player 3 is an ally now
    taunt(me, 63)
    step(b)
    assert b.foe == 1
