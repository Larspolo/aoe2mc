"""game/gather.py: the units of a group in formation walk at the speed of the slowest unit of the group (#3415), as the
AoE2 formations do: a knight and a militia walk at the speed of the militia, a knight alone at its own speed."""
from test_formation_line import setup

from game import ai, train


def command(g, uuid, name, rate):
    return ai.speed_command(uuid, name, g.map.T, ai.NORMAL * rate)


def test_a_knight_in_a_group_walks_at_the_speed_of_the_militia():
    server, g = setup({"k": ("KNIGHT", 14, 25), "m": ("MILITIA", 15, 25)})
    g.choose({"k", "m"}, "k")
    g.walk_to("Steve", (15, 13))
    knight, militia = train.speed(g, "KNIGHT", "k"), train.speed(g, "MILITIA", "m")
    assert ai.walk_speed("KNIGHT", 1) * knight > ai.walk_speed("MILITIA", 1) * militia   # the knight is the faster unit
    assert command(g, "m", "MILITIA", militia) in server.log                         # the slowest unit keeps its speed
    # the knight walks at the militia's tiles per second: its own rate scaled to the speed of the militia
    assert command(g, "k", "KNIGHT", ai.walk_speed("MILITIA", 1) * militia / ai.walk_speed("KNIGHT", 1)) in server.log
    assert command(g, "k", "KNIGHT", knight) not in server.log


def test_a_knight_alone_walks_at_its_own_speed():
    server, g = setup({"k": ("KNIGHT", 14, 25)})
    g.choose({"k"}, "k")
    g.walk_to("Steve", (15, 13))
    assert command(g, "k", "KNIGHT", train.speed(g, "KNIGHT", "k")) in server.log
