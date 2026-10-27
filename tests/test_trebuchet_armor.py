"""game/trebuchet.py: a packed trebuchet has 2 melee and 8 pierce armor, an unpacked one 1 and 150 (AoE2 DE wiki
infobox "Trebuchet", #1409). The armor changes when the pack or the unpack ends. Fake server, no Minecraft."""
from test_train_castle import setup

from game import combat, train, trebuchet


def armor(cmd):
    """(melee, pierce, classes) of an `aoe stats` command."""
    return int(cmd.split()[5]), int(cmd.split()[6]), cmd.split()[8]


def stats_of(server, u="t"):
    return [armor(c) for c in server.log if c.startswith(f"aoe stats {u} ")]


def treb():
    server, g = setup()
    g.soldiers["t"] = "TREBUCHET"
    trebuchet.tick(g, 0.0)                                             # a new trebuchet is packed
    server.log.clear()
    return server, g


def test_the_packed_values_are_the_base_values():
    s = combat.stats("TREBUCHET")
    assert (s.melee, s.pierce, s.classes) == (2, 8, ("siege",)) and trebuchet.UNPACKED == (1, 150)


def test_the_unpack_gives_the_unpacked_armor_and_the_pack_the_packed_armor():
    server, g = treb()
    assert armor(trebuchet.stats_command(g, "t")) == (2, 8, "siege")
    g.choose({"t"}, "t")
    g.attack("fort")
    trebuchet.tick(g, 11.0)
    assert stats_of(server) == []                                      # still packed while it unpacks
    trebuchet.tick(g, 0.2)
    assert stats_of(server) == [(1, 150, "siege,ram")] and trebuchet.state(g, "t") == "unpacked"
    server.log.clear()
    trebuchet.move(g, "t", [])
    trebuchet.tick(g, 5.0)
    assert stats_of(server) == [] and trebuchet.stats(g, "t").pierce == 150   # still unpacked while it packs
    trebuchet.tick(g, 6.2)
    assert stats_of(server) == [(2, 8, "siege")] and trebuchet.state(g, "t") == "packed"


def test_a_research_keeps_the_armor_of_the_state():
    server, g = treb()
    g.choose({"t"}, "t")
    g.attack("fort")
    trebuchet.tick(g, 11.2)
    server.log.clear()
    train.research(g, {"name": "SIEGE_ENGINEERS", "player": "Steve"})   # a change of the trebuchet values
    assert stats_of(server) == [(1, 150, "siege,ram")]                     # not the packed armor of train.stats
    assert trebuchet.stats(g, "t").range == train.stats(g, "TREBUCHET").range > combat.stats("TREBUCHET").range
