"""Unique technology of the Japanese (#4275): the castle of the Japanese researches Kataparuto in the Imperial Age, with
the values of the AoE2 DE wiki ("Unique technology"). Only the Japanese have it (the key "civ" of data/train.jsonl).
Kataparuto: trebuchets pack and unpack 4 times faster (the key "pack_time") and shoot 33% faster (the key "effect")."""
import pytest
from test_train_castle import menus, setup

from game import combat, train, trebuchet

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_japanese_researches_kataparuto():
    server, g = setup("JAPANESE", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'KATAPARUTO')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "KATAPARUTO") is None


def test_kataparuto_packs_and_unpacks_faster_and_reloads_faster():
    server, g = setup("JAPANESE", food=3000, wood=3000, gold=3000, ages=3)
    treb = train.stats(g, "TREBUCHET")
    assert train.queue(g, "Steve", CASTLE, "KATAPARUTO")
    train.tick(g, train.seconds(g, "KATAPARUTO", "CASTLE"))
    assert "KATAPARUTO" in g.techs
    assert trebuchet.pack_time(g) == pytest.approx(trebuchet.PACK * 0.25)
    assert train.stats(g, "TREBUCHET").reload == pytest.approx(combat.stats("TREBUCHET").reload * 0.75)
    assert train.stats(g, "TREBUCHET").reload < treb.reload
    g.soldiers["t"] = "TREBUCHET"
    trebuchet.tick(g, 0.0)
    g.choose({"t"}, "t")
    g.attack("fort")                                                  # no position: in range (#1400)
    assert trebuchet.state(g, "t") == "unpacking"
    assert g.trebs["t"][1] == pytest.approx(trebuchet.PACK * 0.25)
