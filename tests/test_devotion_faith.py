"""Devotion and Faith (#1584): the monastery researches Devotion in the Castle Age (100 food, 200 gold, 40 s) and
Faith after it in the Imperial Age (550 food, 750 gold, 60 s), as on the AoE2 DE wiki infoboxes. Then an enemy monk
needs more conversion intervals for a unit of the player: +1 s and +4 s of minimum and maximum time."""
from types import SimpleNamespace

from test_monk_convert import setup, until_converted
from test_monk_train import MONASTERY, monastery

from game import civs, gather, monk, train


def test_the_values_are_those_of_aoe2():
    assert train.BY_KEY["after"]["FAITH"] == "DEVOTION"
    assert all(len(train.HELP[t]) <= 50 for t in ("DEVOTION", "FAITH"))
    assert "DEVOTION" not in civs.MISSING and {"DANES", "MAGYARS", "TATARS"} <= set(civs.MISSING["FAITH"])


def research(g, food, gold):
    g.stock |= {"food": food, "gold": gold}
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, train.MORE) == 1 and g.stock["food"] == g.stock["gold"] == 0
    return rect


def test_the_monastery_researches_devotion_then_faith_in_one_slot():
    server, g = monastery(age=1)
    train.open_menu(g, "Steve", MONASTERY)
    assert "Devotion" not in server.log[-1]                              # the Feudal Age: hidden
    server, g = monastery(age=2)
    rect = research(g, 100, 200)
    train.tick(g, 40)
    assert "DEVOTION" in g.techs
    train.open_menu(g, "Steve", MONASTERY)
    assert "Faith" not in server.log[-1]                                 # the Castle Age: hidden
    server, g = monastery(age=3)
    g.techs.add("DEVOTION")
    rect = research(g, 550, 750)
    assert g.queues[rect][0]["name"] == "FAITH"
    train.tick(g, 60)
    assert "FAITH" in g.techs


def times(techs, chance):
    """AoE2 seconds until the monk of player 1 converts a militia of player 2 (a bot) with techs; chance 0: the
    random tries always convert, 1: never (only the sure interval)."""
    server, g = setup(("foe", "MILITIA", 2, 12.5))
    g.bots = [SimpleNamespace(g=gather.Gather(server, g.data, player=2))]       # owners.give reads its lists (#2993)
    g.bots[0].g.techs = set(techs)
    g.chance.random = lambda: chance
    monk.convert_order(g, {"monk"}, "foe")
    return until_converted(g, "foe", limit=30) / monk.INTERVAL


def test_devotion_and_faith_make_the_units_of_the_player_resist_conversion():
    assert (times((), 0), times((), 1)) == (5, 9)
    assert (times(("DEVOTION",), 0), times(("DEVOTION",), 1)) == (6, 10)
    assert (times(("DEVOTION", "FAITH"), 0), times(("DEVOTION", "FAITH"), 1)) == (9, 13)   # 5 s more in all


def test_the_techs_of_the_monk_player_do_not_help_the_target():
    server, g = setup(("foe", "MILITIA", 2, 12.5))
    g.techs |= {"DEVOTION", "FAITH"}
    assert monk.resist(g, "foe") == 0 and monk.resist(g, "monk") == 4
