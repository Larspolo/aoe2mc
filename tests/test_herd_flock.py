"""A captured herdable is in the flock of its new owner (#2995): a right click selects it, and the new owner's
`herd()` and `pickable` have it. The old owner's flock loses it."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import herd  # noqa: E402

T = 4
SHEEP, SCOUT = "00000000-0000-0000-0000-00000000005e", "00000000-0000-0000-0000-000000000001"
PLAYERS = {"1": {"color": "blue"}, "2": {"color": "red"}}


def bare(player, objects):
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map, g.paper, g.players = player, {"objects": objects}, types.SimpleNamespace(T=T), True, PLAYERS
    g.villagers, g.soldiers, g.selected, g.dead, g.bots = {}, {}, set(), {}, []
    g.prey = {o["uuid"]: o["name"] for o in objects if o["player"] in (0, player)}
    g.enemies = {o["uuid"]: o["name"] for o in objects if o["player"] not in (0, player)}
    g.flock = {o["uuid"] for o in objects if o["player"] == player}
    g.garrisons = {}
    g.sent = []
    g.command, g.clock = g.sent.append, lambda: 0.0
    g.set = lambda v, state: setattr(v, "state", state)
    return g


def test_a_gaia_sheep_taken_by_a_scout_is_in_the_flock_and_pickable():
    sheep = {"kind": "unit", "name": "SHEEP", "player": 0, "uuid": SHEEP, "tile": [10.0, 10.0]}
    objects = [sheep]
    g = bare(1, objects)
    g.soldiers = {SCOUT: "SCOUT_CAVALRY"}
    objects.append({"kind": "unit", "name": "SCOUT_CAVALRY", "player": 1, "uuid": SCOUT})
    b = bare(2, objects)
    g.bots = [types.SimpleNamespace(g=b)]
    near = (10 * T + 0.5 * T, 70.0, 10 * T)                   # next to the sheep, within 2 tiles
    g.where = lambda want: {u: p for u, p in {SCOUT: near, SHEEP: near}.items() if u in want}
    herd.tick(g)                                             # the first look: the clock is 0.0
    assert sheep["player"] == 1
    assert SHEEP in g.herd() and SHEEP in g.pickable()


def test_a_sheep_taken_from_another_player_leaves_its_flock():
    sheep = {"kind": "unit", "name": "SHEEP", "player": 2, "uuid": SHEEP, "tile": [10.0, 10.0]}
    objects = [sheep]
    g = bare(1, objects)
    b = bare(2, objects)
    g.bots = [types.SimpleNamespace(g=b)]
    assert SHEEP in b.flock and SHEEP not in g.flock
    herd.take(g, [g, b], sheep, 1)
    assert SHEEP in g.flock and SHEEP not in b.flock
