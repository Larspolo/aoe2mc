"""Fabric Shields (#2047): the castle of the Incas researches it in the Imperial Age. The kamayuks and the slingers get
more melee and pierce armor."""
from test_train_castle import setup

from game import combat, train

CASTLE = (12, 4)


def test_the_effect_changes_the_live_and_the_new_units():
    server, g = setup("INCAS", food=2000, wood=0, gold=2000, ages=3)
    before = train.stats(g, "SLINGER")
    assert train.queue(g, "Steve", CASTLE, "FABRIC_SHIELDS")
    train.tick(g, train.TRAIN_TIMES["FABRIC_SHIELDS"])
    assert "FABRIC_SHIELDS" in g.techs
    after = train.stats(g, "SLINGER")
    assert after.melee > before.melee and after.pierce > before.pierce
    assert train.stats(g, "KAMAYUK").melee > combat.stats("KAMAYUK").melee
    assert train.stats(g, "ARBALESTER").melee == combat.stats("ARBALESTER").melee   # not a kamayuk or slinger
