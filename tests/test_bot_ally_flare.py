"""game/bot.py: taunt 46 of an ally puts a flare at the center of the bot army, 47 sends the army to the last flare of
the ally (#4888), on the map of test_bot_gather (the bot is player 2, the person is player 1)."""
import ai  # noqa: E402
import flare  # noqa: E402
from test_bot_gather import bot_map

from game.bot import build  # noqa: F401  (puts game/ on the path for the plain names)


def setup(monkeypatch, ally=True):
    server, me, b = bot_map()
    for p in ("1", "2"):
        b.g.players.setdefault(p, {})
    if ally:
        b.g.players["1"]["team"] = b.g.players["2"]["team"] = 1
    for i, (x, z) in enumerate([(10.5, 10.5), (14.5, 12.5)]):
        b.g.soldiers[f"s{i}"] = "MILITIA"
        server.entities[f"s{i}"] = {"Pos": (x, 64.0, z), "Rotation": (0.0, 0.0)}
    server.entities["e0"] = {"Pos": (5.5, 64.0, 26.5)}
    b.g.enemies["e0"] = "MILITIA"
    put, attacks, walks, said = [], [], [], []
    monkeypatch.setattr(flare, "put", lambda g, who, x, y, z: put.append((g.player, x, y, z)))
    monkeypatch.setattr(ai, "attack", lambda game, us, names, T, t, speeds: attacks.append((us, t)))
    monkeypatch.setattr(b.g, "walk_to", lambda name, cell, units=None: walks.append((cell, sorted(units))))
    command = b.g.command
    monkeypatch.setattr(b.g, "command", lambda c: (said.append(c) if c.startswith("tellraw") else None) or command(c))
    return me, b, put, attacks, walks, said


def taunt(me, n):
    me.taunted = [*getattr(me, "taunted", []), str(n)]   # as gather.Game.clicks keeps them (#4827)


def test_taunt_46_flares_the_center_of_the_army(monkeypatch):
    me, b, put, attacks, walks, said = setup(monkeypatch)
    taunt(me, 46)
    b.obey()
    assert put == [(2, 12, 64, 11)]


def test_taunt_47_attacks_near_the_last_flare(monkeypatch):
    me, b, put, attacks, walks, said = setup(monkeypatch)
    me.flares = [(20, 64, 20, me.clock() + 10), (6, 64, 25, me.clock() + 10)]
    taunt(me, 47)
    b.obey()
    assert attacks == [(["s0", "s1"], "e0")] and b.targets == {"s0": "e0", "s1": "e0"}
    me.flares = [(28, 64, 4, me.clock() + 10)]             # no enemy near this flare: they walk there
    taunt(me, 47)
    b.obey()
    assert walks == [((28, 4), ["s0", "s1"])] and not said


def test_taunt_47_with_no_live_flare_says_one_line(monkeypatch):
    me, b, put, attacks, walks, said = setup(monkeypatch)
    me.flares = [(6, 64, 25, me.clock() - 1)]
    taunt(me, 47)
    b.obey()
    assert len(said) == 1 and not attacks and not walks


def test_an_enemy_taunt_changes_nothing(monkeypatch):
    me, b, put, attacks, walks, said = setup(monkeypatch, ally=False)
    me.flares = [(6, 64, 25, me.clock() + 10)]
    for n in (46, 47):
        taunt(me, n)
    b.obey()
    assert not put and not attacks and not walks and not said
