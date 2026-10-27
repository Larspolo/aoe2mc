"""game/train.py research(): a packed trebuchet keeps range 0 after Siege Engineers, so that it cannot shoot while it
is packed (AoE2 DE); an unpacked one gets the new range (#1414). Fake server, no Minecraft."""
from test_trebuchet_armor import treb

from game import train, trebuchet


def ranges(server, u="t"):
    """The ranges in blocks of the `aoe range` commands of unit u."""
    return [float(c.split()[3]) for c in server.log if c.startswith(f"aoe range {u} ")]


def research(g):
    train.research(g, {"name": "SIEGE_ENGINEERS", "player": "Steve"})   # +1 range of the trebuchet


def test_a_packed_trebuchet_keeps_range_0_after_a_research():
    server, g = treb()
    research(g)
    assert trebuchet.state(g, "t") == "packed" and all(r == 0 for r in ranges(server))


def test_a_trebuchet_that_unpacks_gets_the_new_range_at_the_end_of_the_unpack():
    server, g = treb()
    g.choose({"t"}, "t")
    g.attack("fort")
    trebuchet.tick(g, 5.0)
    research(g)
    assert all(r == 0 for r in ranges(server))
    trebuchet.tick(g, 6.2)
    assert ranges(server)[-1] == float(trebuchet.range_command(g, "t").split()[3]) > 0


def test_an_unpacked_trebuchet_gets_the_new_range():
    server, g = treb()
    g.choose({"t"}, "t")
    g.attack("fort")
    trebuchet.tick(g, 11.2)
    old = ranges(server)[-1]
    server.log.clear()
    research(g)
    assert ranges(server) == [float(trebuchet.range_command(g, "t").split()[3])] and ranges(server)[0] > old
