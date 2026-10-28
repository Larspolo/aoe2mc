"""A path search to an enclosed goal ends after CLOSED cells (#2881): in de-64.3 an order of 13 units to such a goal took 12
searches of 20000 cells, held the live replay for 8 s, and the walks of the next 30 s started late (stuck units)."""
import numpy as np

from game import gather


def grid(rows):
    """aoe2mc.json data from rows of ground heights (None = water) with tile size 1."""
    return {"tile_size": 1, "ground": [" ".join("-" if y is None else str(y) for y in r) for r in rows], "objects": []}


def test_the_path_is_the_same_with_and_without_the_closed_check(monkeypatch):
    monkeypatch.setattr(gather, "CLOSED", 5)                           # the check after 5 cells, a flood of 10
    rng = np.random.default_rng(2881)
    for _ in range(40):
        n = 24
        rows = [[None if rng.random() < 0.25 else int(64 + rng.integers(0, 3)) for _ in range(n)] for _ in range(n)]
        m = gather.Map(grid(rows))
        cells = [(int(x), int(z)) for x, z in rng.integers(0, n, (8, 2))]
        start, goals = cells[0], set(cells[1:1 + int(rng.integers(1, 4))])
        fast = m.path(start, goals, 20000)
        with monkeypatch.context() as p:
            p.setattr(gather.Map, "closed", lambda *a, **k: False)
            assert m.path(start, goals, 20000) == fast


def test_an_enclosed_goal_needs_no_search():
    rows = [[64] * 200 for _ in range(200)]
    for d in range(-2, 3):                                             # a wall of water around (150, 150)
        for x, z in ((150 + d, 148), (150 + d, 152), (148, 150 + d), (152, 150 + d)):
            rows[z][x] = None
    m = gather.Map(grid(rows))
    calls = []
    m.free = lambda x, z, free=m.free: calls.append(1) or free(x, z)
    assert m.path((10, 10), {(150, 150)}, 20000) is None and len(calls) < 4 * 8 * gather.CLOSED   # not 20000 cells
    assert m.closed((10, 10), {(150, 150)}, m.free)
    assert not m.closed((149, 150), {(150, 150)}, m.free)              # the start is in the region
    assert m.path((149, 150), {(150, 150)}) == [(150, 150)]
