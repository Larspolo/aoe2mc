"""#2990: save a played game with player 1 and a bot, load it through run.play() and compare the whole state of each
side and of its Map. tests/test_savegame_fields.py sees only the lines `g.x = ...`: this test also sees the fields of
__init__, of gather.Map, the objects that the sides share and the types (gather.Endless)."""
import json
import os
import random
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import build  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402
import savegame  # noqa: E402
import score  # noqa: E402
from test_gather import FakeServer  # noqa: E402

UNEQUAL = (                                                            # fields of a side that a load cannot keep equal,
    "chance",                                                          # one per line with its reason: a new seeded random
    "game",                                                            # the server object of the new session
    "shown",                                                           # the sidebar values that the load shows again
    "t0",                                                              # the clock of the new session
)
MAP_UNEQUAL = ()                                                       # the same for the fields of a gather.Map
GAPS = {                                                               # path: the ticket that fixes the gap of the load
}


class Server(FakeServer):
    kind, game_port, version = "vanilla", 0, "26.3"

    def __init__(self, entities):
        super().__init__(entities)
        self.sides = {}

    def forceload(self):
        pass


def entities(world):
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    m = gather.Map(data)
    return {o["uuid"]: {"Pos": (x + 0.5, m.y(x, z), z + 0.5), "Rotation": (0.0, 0.0)}
            for o in data["objects"] if o["kind"] == "unit"
            for x, z in [(int(o["tile"][0] * m.T), int(o["tile"][1] * m.T))]}


def play(world, monkeypatch, state=None):
    monkeypatch.setattr(gather.Gather, "run", lambda self, seconds=None: None)
    return run.play(Server(entities(world)), world, bot=True, state=state)


def played(g):
    """Play some turns of the game of g: a farm, a lumber camp and a gate of player 1, a site that stays a site, a
    razed enemy house, a farmer on the farm and more stock."""
    for name, rect in (("FARM", (40, 52, 40, 52)), ("LUMBER_CAMP", (8, 16, 44, 52)), ("PALISADE_GATE", (24, 28, 52, 56))):
        build.rise(g, build.found(g, name, rect, free=True), 1e6)
    build.found(g, "HOUSE", (52, 60, 8, 16), free=True)               # a site with no builder
    score.razed(g, "house-of-player-2")
    g.stock["wood"] += 123
    g.send(next(iter(g.map.farms)), set(g.villagers))
    g.bots[0].g.stock["gold"] += 45


def diff(a, b, path, seen):
    """The paths below path where b differs from a: the values, the types and the fields of the objects."""
    if (id(a), id(b)) in seen:
        return []
    seen.add((id(a), id(b)))
    if type(a) is not type(b):
        return [f"{path}: type {type(a).__name__} != {type(b).__name__}"]
    if isinstance(a, random.Random):
        return []
    if isinstance(a, np.ndarray):
        return [] if a.shape == b.shape and (a == b).all() else [path]
    if isinstance(a, dict):
        if set(a) != set(b):
            return [f"{path}: keys {sorted(map(str, set(a) ^ set(b)))[:5]}"]
        return [d for k in a for d in diff(a[k], b[k], f"{path}[{k!r}]", seen)]
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, f"{path}[{i}]", seen)]
    if hasattr(a, "__dict__") and not isinstance(a, type):
        return fields(a, b, path, seen, ())
    return [] if a == b else [path]


def fields(a, b, path, seen, skip):
    names = (set(vars(a)) | set(vars(b))) - set(skip)
    return [f"{path}.{k}: missing" if k not in vars(a) or k not in vars(b) else d
            for k in sorted(names) for d in ([None] if k not in vars(a) or k not in vars(b)
                                             else diff(vars(a)[k], vars(b)[k], f"{path}.{k}", seen))]


def gaps(g, h):
    """The differences of the sides of g and h, without NOT_SAVED, UNEQUAL and GAPS."""
    out = []
    for i, (x, y) in enumerate(zip(savegame.sides(g), savegame.sides(h))):
        seen = {(id(x.map), id(y.map))}
        out += fields(x, y, f"side{i}", seen, (*savegame.NOT_SAVED, *UNEQUAL))
        out += fields(x.map, y.map, f"side{i}.map", set(), MAP_UNEQUAL)
    return [p for p in out if p.split(":")[0] not in GAPS]


def shared(g):
    """The pairs of paths (side field, side field or map field) of g that hold the same mutable object."""
    where = {}
    for i, x in enumerate(savegame.sides(g)):
        for k, v in [*vars(x).items(), *((f"map.{k}", v) for k, v in vars(x.map).items())]:
            if k not in savegame.NOT_SAVED and k not in UNEQUAL and isinstance(v, (dict, list, set)):
                where.setdefault(id(v), []).append(f"side{i}.{k}")
    return {(p, q) for ps in where.values() for p in ps for q in ps if p < q}


@pytest.fixture(scope="module")
def games(tiny_world):
    with pytest.MonkeyPatch.context() as mp:
        g = play(tiny_world[0], mp)
        played(g)
        h = play(tiny_world[0], mp, json.loads(json.dumps(savegame.dump(g))))
    return g, h


def test_a_load_keeps_the_whole_state_of_each_side(games):
    g, h = games
    assert len(savegame.sides(g)) == len(savegame.sides(h)) == 2           # player 1 and the bot
    assert len(g.sites) == 4 and g.farmers and g.razed and g.map.farms     # the game changed the state
    assert gaps(g, h) == []


def test_a_load_keeps_the_objects_that_the_sides_share(games):
    g, h = games
    assert shared(g) and shared(h) == shared(g)


def test_the_test_sees_a_field_that_only_the_first_game_sets(games):
    g, h = games
    g.new_field = {"a": 1}
    try:
        assert gaps(g, h) == ["side0.new_field: missing"]
    finally:
        del g.new_field


def test_the_test_sees_two_sides_that_no_longer_share_an_object(games):
    g, h = games
    b = h.bots[0].g.map
    trees, b.trees = b.trees, dict(b.trees)
    try:
        assert ("side0.map.trees", "side1.map.trees") in shared(g) - shared(h)
    finally:
        b.trees = trees
