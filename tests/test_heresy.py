"""Heresy (#1582): the monastery researches it in the Castle Age (1000 gold, 60 s, AoE2 DE wiki "Heresy"). Then a unit
of the player that an enemy monk converts dies, with its horse or rider, and the enemy gets no unit."""
from types import SimpleNamespace

from test_monk_convert import setup, until_converted
from test_monk_techs import MONASTERY, research
from test_monk_train import monastery

from game import civs, gather, monk, train


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["HERESY"]) <= 50
    assert {"BRITONS", "GOTHS", "PERSIANS", "WU"} <= set(civs.MISSING["HERESY"])
    assert not {"AZTECS", "FRANKS", "TEUTONS"} & set(civs.MISSING["HERESY"])


def test_the_monastery_researches_it_in_slot_6_in_the_castle_age():
    server, g = monastery(age=1)
    g.stock["gold"] = 1000
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, 6) == 0 and g.stock["gold"] == 1000
    server, g = monastery(age=2)
    rect = research(g, 6, 1000)
    assert g.queues[rect][0]["name"] == "HERESY"
    train.tick(g, 60)
    assert "HERESY" in g.techs


def converted(heretic):
    """The own monk converts the militia "foe" of player 2; heretic: player 2 has Heresy (a bot of g)."""
    server, g = setup(("foe", "MILITIA", 2, 12.5))
    g.bots = [SimpleNamespace(g=gather.Gather(server, g.data, player=2))]       # owners.give reads its lists (#2993)
    g.bots[0].g.techs = {"HERESY"} if heretic else set()
    g.chance.seed(1)
    assert monk.convert_order(g, {"monk"}, "foe")
    until_converted(g, "foe")
    return server, g


def test_a_converted_unit_of_a_player_with_heresy_dies():
    server, g = converted(True)
    assert "foe" not in g.enemies and "foe" not in g.soldiers and "foe" not in g.converting
    assert {"kill foe", "execute as foe on vehicle run kill @s", "execute as foe on passengers run kill @s"} <= set(server.log)
    assert "team join p1 foe" not in server.log
    assert monk.heresy(g, 2) and not monk.heresy(g, 1)


def test_without_heresy_the_unit_changes_sides():
    server, g = converted(False)
    assert "foe" in g.soldiers and "kill foe" not in server.log


def test_a_bot_sees_the_heresy_of_the_human_player_that_it_shares():
    server, g = setup()
    g.share = SimpleNamespace(player=3, techs={"HERESY"})
    assert monk.heresy(g, 3) and not monk.heresy(g, 2)
