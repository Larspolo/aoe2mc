"""Unique technology of the Armenians (#4273): the castle of the Armenians researches Fereters in the Imperial Age:
infantry except the Spearman line gets +30 hit points (AoE2 DE wiki "Unique technology"). Only the Armenians have it
(the key "civ" of data/train.jsonl)."""
import combat
from test_train_castle import setup

from game import train

CASTLE = (12, 4)


def test_fereters_hits_only_the_castle_of_the_armenians():
    server, g = setup("ARMENIANS", ages=3)
    assert train.layout(g, train.home(g, CASTLE)).get("FERETERS", (None, None, None))[2] is not None
    server, g = setup("TURKS", ages=3)
    assert train.layout(g, train.home(g, CASTLE)).get("FERETERS", (None, None, None))[2] is None


def test_fereters_adds_hp_to_infantry_but_not_spearmen():
    server, g = setup("ARMENIANS", food=3000, wood=3000, gold=3000, ages=3)
    champion = train.stats(g, "CHAMPION")
    halberdier = train.stats(g, "HALBERDIER")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "FERETERS")
    train.tick(g, train.seconds(g, "FERETERS", "CASTLE"))
    assert "FERETERS" in g.techs
    assert train.stats(g, "CHAMPION").hp == combat.stats("CHAMPION").hp + 30
    assert train.stats(g, "CHAMPION").hp > champion.hp
    assert train.stats(g, "HALBERDIER").hp == halberdier.hp     # the Spearman line
    assert train.stats(g, "KNIGHT").hp == knight.hp            # cavalry: not infantry
