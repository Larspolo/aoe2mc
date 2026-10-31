"""game/per.py: the orders of all units of a type (#4967): up-garrison, up-ungarrison, up-gather-inside, up-guard-unit,
up-retreat-to, up-set-attack-stance, up-delete-objects and up-get-guard-state reach the paths of the game program."""
import garrison as plain_garrison
import stance as plain_stance
from test_bot_gather import bot_map

from game import garrison, per, stance, train


def army(monkeypatch):
    """The bot of bot_map with two militia, a spearman, its town center (TC) and a log of the paths."""
    server, me, b = bot_map()
    g = b.g
    g.paper = True
    for u, n in (("m0", "MILITIA"), ("m1", "MILITIA"), ("s0", "SPEARMAN")):
        g.soldiers[u] = n
        server.entities[u] = {"Pos": (6.5, 64.0, 6.5), "Rotation": (0.0, 0.0), "Health": 10.0}
    log = []
    for m in (garrison, plain_garrison):                               # per imports the plain names (LEARNINGS)
        monkeypatch.setattr(m, "order", lambda g, p, cell: log.append(("garrison", sorted(g.selected), cell)) or cell)
        monkeypatch.setattr(m, "out", lambda g, rect: log.append(("out", rect)) or [])
    for m in (stance, plain_stance):
        monkeypatch.setattr(m, "put", lambda g, s: log.append(("stance", sorted(g.selected), s)))
        monkeypatch.setattr(m, "delete_units", lambda g, us: log.append(("delete", sorted(us))))
    monkeypatch.setattr(g, "walk_to", lambda p, at, us: log.append(("walk", tuple(at), sorted(us))))
    s = per.Script(per.parse(""), b)
    s.objects(g)                                                     # the ids of the own objects
    tc = next(r for r, o in garrison.holders(g).items() if o["name"] == "TOWN_CENTER")
    return server, b, s, log, tc


def test_garrison_ungarrison_and_gather_inside(monkeypatch):
    server, b, s, log, tc = army(monkeypatch)
    s.act(None, ("up-garrison", "c:", "town-center", "c:", "militiaman"))
    assert log.pop() == ("garrison", ["m0", "m1"], (tc[0], tc[2]))
    assert not b.g.selected
    s.act(None, ("up-ungarrison", "c:", "town-center"))
    assert log.pop() == ("out", tc)
    s.act(None, ("up-gather-inside", "c:", "town-center", 1))
    train.go(b.g, tc, "m9", "MILITIA")                                 # a new unit of the town center goes inside
    assert log.pop() == ("garrison", ["m9"], (tc[0], tc[2]))
    s.act(None, ("up-gather-inside", "c:", "town-center", 0))
    train.go(b.g, tc, "m9", "MILITIA")
    assert not log


def test_guard_retreat_stance_and_delete(monkeypatch):
    server, b, s, log, tc = army(monkeypatch)
    v = sorted(b.g.villagers)[0]
    b.g.positions = lambda us: {u: (9.5, 64.0, 9.5) for u in us}
    s.act(None, ("up-guard-unit", "c:", s.ids[v], "c:", "spearman"))
    assert log.pop() == ("stance", ["s0"], "defensive")
    b.wave = {"m0"}
    s.act(None, ("up-retreat-to", "c:", s.ids[v], "c:", "militiaman"))
    assert log.pop() == ("walk", (9.5, 9.5), ["m0", "m1"]) and not b.wave
    s.act(None, ("up-set-attack-stance", "c:", "militiaman", 2))      # airef: 2 is stand ground
    assert log.pop() == ("stance", ["m0", "m1"], "stand_ground")
    b.hp = lambda u: {"m0": 5.0, "m1": 40.0}.get(u)
    s.act(None, ("up-delete-objects", "c:", "militiaman", "c:", 10))
    assert log.pop() == ("delete", ["m0"])


def test_guard_state_and_an_unknown_stance(monkeypatch, capsys):
    server, b, s, log, tc = army(monkeypatch)
    b.guards = {"m0": ("e1", (0, 0, 0)), "m1": ("e1", (0, 0, 0))}
    s.act(None, ("up-get-guard-state", 100))
    assert [s.goals[100 + i] for i in range(4)] == [1, 1, 2, 0]
    s.act(None, ("up-set-attack-stance", "c:", "militiaman", 7))
    assert "attack stance 7" in capsys.readouterr().err and not log
