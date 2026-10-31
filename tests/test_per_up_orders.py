"""game/per.py: the army and building orders of an AI script (#4876): up-reset-attack-now, up-retreat-now,
up-reset-unit, up-reset-building, up-delete-idle-units and up-delete-distant-farms."""
from test_bot_gather import bot_map

from game import per
from game.bot import train  # the module that per uses

TEXT = """
(defrule (true) => (attack-now) (disable-self))
(defrule (goal 1 1) => (up-reset-attack-now) (up-retreat-now) (up-reset-unit c: militiaman))
(defrule (goal 1 2) => (up-reset-building 1 c: town-center) (up-delete-idle-units idle-type-villager)
                       (up-delete-distant-farms c: 8))
"""


def army():
    """A bot with an army in a wave far from home, a queue of a villager and Loom, and a near and a far farm."""
    server, me, b = bot_map()
    g = b.g
    g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    for i in range(3):
        g.soldiers[f"m{i}"] = "MILITIA"
        server.entities[f"m{i}"] = {"Pos": (5.5 + i, 64.0, 5.5), "Rotation": (0.0, 0.0)}
    b.wave, b.targets = {"m0", "m1"}, {"m0": "p1"}
    rect = next(r for r, n in train.homes(g).items() if n == "TOWN_CENTER")
    for n in ("VILLAGER_MALE", "LOOM", "VILLAGER_MALE"):
        train.queue(g, b.nobody, (rect[0], rect[2]), n)
    for fp in ([24, 27, 25, 28], [8, 11, 8, 11]):                        # x0, x1, z0, z1: near the town center, far from it
        g.sites.append({"name": "FARM", "player": g.player, "footprint": fp, "done": True, "progress": 1})
    s = per.Script(per.parse(TEXT), b)
    b.script = s
    return server, b, s, rect


def test_the_six_orders():
    server, b, s, rect = army()
    g = b.g
    s.step()
    assert s.attacking
    s.goals[1] = 1
    s.step()
    assert not s.attacking                                             # up-reset-attack-now
    assert not b.wave and not b.targets                                # up-retreat-now: all soldiers walk home
    assert [n for n, _, _ in train.groups(g.queues[rect])] == ["VILLAGER_MALE", "LOOM", "VILLAGER_MALE"]
    s.goals[1] = 2
    for v in g.villagers.values():
        g.set(v, "idle")
    sent, command = [], g.command
    g.command = lambda c: sent.append(c) or command(c)
    s.step()
    assert [e["name"] for e in g.queues[rect]] == ["LOOM"]             # option 1 keeps the research
    assert all(any(c == f"execute as {u} if entity @s[tag=!aoe2mc.keep] run kill @s" for c in sent)
               for u in g.villagers)                                   # up-delete-idle-units
    from game import combat
    assert f"aoe destroy {combat.target_uuid([8, 8, 11, 11])}" in sent  # the far farm falls
    assert f"aoe destroy {combat.target_uuid([24, 25, 27, 28])}" not in sent


def test_the_commands_of_the_orders():
    server, b, s, rect = army()
    sent = []
    command = b.g.command
    b.g.command = lambda c: sent.append(c) or command(c)
    s.act(None, ("up-retreat-now",))
    assert not b.wave
    s.act(None, ("up-reset-unit", "c:", "militiaman"))
    assert {f"aoe stop m{i}" for i in range(3)} <= set(sent)
    for v in b.g.villagers.values():
        b.g.set(v, "idle")
    s.act(None, ("up-delete-idle-units", "idle-type-villager"))
    assert any(c.startswith(f"execute as {u} ") and c.endswith("run kill @s") for c in sent for u in b.g.villagers)
    s.act(None, ("up-delete-distant-farms", "c:", 8))
    assert any(c.startswith("aoe destroy") for c in sent)


def test_option_0_resets_the_research_too():
    server, b, s, rect = army()
    s.act(None, ("up-reset-building", 0, "c:", "town-center"))
    assert not b.g.queues[rect]


def test_an_unknown_idle_type_warns(capsys):
    server, b, s, rect = army()
    s.act(None, ("up-delete-idle-units", "idle-type-ghost"))
    assert "unknown idle type idle-type-ghost" in capsys.readouterr().err

