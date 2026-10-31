"""up-*-in-town, up-defender-count and up-idle-unit-count of an AI script (#4874). The map of test_bot_gather: player 1
(a person, the enemy) and the bot, player 2, whose town center is at block (21, 21)."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses


def script(text=""):
    server, me, b = bot_map()
    me.bots = [b]                                                      # run.py: player 1 holds the bots
    return per.Script(per.parse(text), b), b, me, server


def far(me, b):
    """Only the enemy objects that the test puts in the town: no own town center of player 1 and its villager away."""
    me.data["objects"] = [o for o in me.data["objects"] if o.get("player") != 1]
    b.g.data["objects"] = me.data["objects"]
    for v in me.villagers.values():
        v.pos = (100.0, 64.0, 100.0)


def test_the_six_town_facts():
    s, b, me, server = script()
    far(me, b)
    for f in ("up-enemy-units-in-town", "up-enemy-villagers-in-town", "up-enemy-buildings-in-town"):
        assert s.check((f, "==", 0))
    v = next(iter(me.villagers.values()))
    v.pos = (18.5, 64.0, 18.5)                                         # an enemy villager in the town
    me.soldiers["s1"] = "MILITIA"                                      # an enemy soldier in the town
    server.entities["s1"] = {"Pos": (19.5, 64.0, 19.5), "Rotation": (0.0, 0.0)}
    me.sites.append({"name": "HOUSE", "player": 1, "footprint": [18, 19, 18, 19], "progress": 0.5})
    assert s.check(("up-enemy-units-in-town", "==", 2)) and s.check(("up-enemy-villagers-in-town", "==", 1))
    assert s.check(("up-enemy-buildings-in-town", "==", 1))
    assert s.check(("up-building-type-in-town", "c:", "house", "==", 1))
    assert s.check(("up-building-type-in-town", "c:", "barracks", "==", 0))
    assert s.check(("up-unit-type-in-town", "c:", "militiaman", "==", 1))
    assert s.check(("up-villager-type-in-town", "c:", "villager", "==", 1))
    per.TOWN, old = 1, per.TOWN
    try:
        assert s.check(("up-enemy-units-in-town", "==", 0))
    finally:
        per.TOWN = old
    assert not s.warned


def test_defender_and_idle_unit_counts():
    s, b, me, server = script("(defrule (up-idle-unit-count idle-villagers >= 5) => (set-goal 1 1))")
    n = len(b.g.villagers)
    assert s.check(("up-idle-unit-count", "idle-villagers", "==", n))  # all start idle
    next(iter(b.g.villagers.values())).state = "chop"
    assert s.check(("up-idle-unit-count", "idle-villagers", "==", n - 1))
    b.g.soldiers.update(a="MILITIA", c="MILITIA")
    b.guards["a"] = ("e", (0, 64, 0))
    assert s.check(("up-idle-unit-count", "idle-military", "==", 1))
    assert s.check(("up-defender-count", "==", 1))
    s.step()
    assert s.goals.get(1) == (1 if n - 1 >= 5 else None)
    assert not s.check(("up-idle-unit-count", "idle-ships", ">=", 0)) and s.warned == {("idle type", "idle-ships")}
