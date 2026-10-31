"""game/bot.py: taunts 76 to 101 of an allied person name the unit that the bot attacks with (#4887). The map of
test_bot_gather: the bot is player 2, the person player 1; the bot has no archery range, so it cannot train archers."""
from test_bot_gather import bot_map


def setup(ally=True):
    server, me, b = bot_map()
    for p in ("1", "2"):
        b.g.players.setdefault(p, {})
    b.g.players["1"]["team"] = 1 if ally else 2
    b.g.players["2"]["team"] = 1
    me.bots = [b]
    return me, b


def taunt(me, n):
    me.taunted = [*getattr(me, "taunted", []), str(n)]   # as gather.Game.clicks keeps them


def test_ally_taunt_names_the_unit():
    me, b = setup()
    taunt(me, 77)
    b.give()
    assert b.unit == ["ARCHER"]


def test_enemy_taunt_names_nothing():
    me, b = setup(ally=False)
    taunt(me, 77)
    b.give()
    assert b.unit is None


def test_no_building_for_the_unit_answers_once(monkeypatch):
    me, b = setup()
    said = []
    command = b.g.command
    monkeypatch.setattr(b.g, "command", lambda c: (said.append(c) if c.startswith("tellraw") else None) or command(c))
    taunt(me, 90)                                                   # monks: no monastery in this map
    b.give()
    assert b.unit == ["MONK"]
    assert len(said) == 1 and "cannot train" in said[0]

