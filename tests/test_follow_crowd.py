"""#3372: a villager that a crowd pushes back and forth near its goal arrives (Gather.follow)."""
from game import gather


def walker(start, positions):
    """A Gather with a fake clock (0.05 s per tick) and a villager at `start`. Each tick it reads the next of
    `positions`. Its goal is the cell (10, 10): the center is (10.5, 10.5)."""
    g = object.__new__(gather.Gather)
    g.now, g.cmds = 0.0, []
    g.clock = lambda: g.now
    g.command = g.cmds.append
    g.set = lambda v, state: None
    g.move = lambda v: g.cmds.append("move")
    g.pos = lambda uuid: next(positions)
    v = gather.Villager("v", start)
    v.goal, v.path, v.state = (10, 10), [(10, 10)], "to_drop"
    return g, v


def tick(g, v, n):
    for _ in range(n):
        g.now += 0.05
        g.follow(v)


def test_pushed_villager_arrives_within_2_seconds():
    # a crowd moves the villager 0.1 blocks back and forth at each tick, 1.8 blocks from the goal center
    g, v = walker((12.3, 0.0, 10.5), iter([(12.4, 0.0, 10.5), (12.3, 0.0, 10.5)] * 100))
    tick(g, v, 40)                                  # 2 s of game time
    assert f"aoe stop {v.uuid}" in g.cmds
    assert v.path == []


def test_walking_villager_still_arrives():
    # a villager that walks 0.2 blocks per tick straight to the goal arrives at its normal speed
    steps = iter([(10.5 + 0.2 * k, 0.0, 10.5) for k in range(19, -1, -1)] + [(10.5, 0.0, 10.5)] * 10)
    g, v = walker((14.5, 0.0, 10.5), steps)
    tick(g, v, 30)
    assert f"aoe stop {v.uuid}" in g.cmds
