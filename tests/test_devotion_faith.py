"""Devotion and Faith (#1584): the monastery researches Devotion in the Castle Age and Faith after it in the Imperial
Age, at the costs and times of game/data/train.jsonl. Then an enemy monk needs more conversion intervals for a unit of
the player: the "resist" intervals of the techs (monk.RESIST)."""
from types import SimpleNamespace

from test_monk_convert import setup, until_converted
from test_monk_train import MONASTERY, monastery

from game import gather, monk, train


TIME = {r["name"]: r["time"] for r in train.ROWS}


def research(g, name):
    g.stock |= {"food": 0, "gold": 0} | train.COSTS[name]
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, train.MORE) == 1 and g.stock["food"] == g.stock["gold"] == 0
    return rect


def test_the_monastery_researches_devotion_then_faith_in_one_slot():
    server, g = monastery(age=1)
    train.open_menu(g, "Steve", MONASTERY)
    assert "Devotion" not in server.log[-1]                              # the Feudal Age: hidden
    server, g = monastery(age=2)
    rect = research(g, "DEVOTION")
    train.tick(g, TIME["DEVOTION"])
    assert "DEVOTION" in g.techs
    train.open_menu(g, "Steve", MONASTERY)
    assert "Faith" not in server.log[-1]                                 # the Castle Age: hidden
    server, g = monastery(age=3)
    g.techs.add("DEVOTION")
    rect = research(g, "FAITH")
    assert g.queues[rect][0]["name"] == "FAITH"
    train.tick(g, TIME["FAITH"])
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
    for techs in (("DEVOTION",), ("DEVOTION", "FAITH")):
        more = sum(monk.RESIST[t] for t in techs)
        assert more > 0 and all(times(techs, c) == times((), c) + more for c in (0, 1)), techs


def test_the_techs_of_the_monk_player_do_not_help_the_target():
    server, g = setup(("foe", "MILITIA", 2, 12.5))
    g.techs |= {"DEVOTION", "FAITH"}
    assert monk.resist(g, "foe") == 0 and monk.resist(g, "monk") == monk.RESIST["DEVOTION"] + monk.RESIST["FAITH"]
