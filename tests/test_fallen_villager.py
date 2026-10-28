"""A fallen own villager of a Tupi player gives its part of the cost back, and a unit with no cost line gives nothing
and no error (#2966). Fake server of test_kill_spoils."""
from test_kill_spoils import game

from game import civs, train


def test_a_fallen_tupi_villager_gives_its_part_and_the_census_runs_on():
    server, g = game("TUPI")
    g.villagers["v"] = None
    server.entities["v"] = {"Pos": (8.5, 64.0, 8.5)}
    train.census(g)
    del server.entities["v"]                                           # killed: no position
    train.census(g)
    assert "v" not in g.villagers
    part = civs.FALLEN["TUPI"]
    cost = train.price(g, "VILLAGER_MALE")
    assert g.stock["food"] == int(cost["food"] * part)
    train.census(g)                                                    # a dead unit gives its part only once
    assert g.stock["food"] == int(cost["food"] * part)


def test_a_fallen_tupi_unit_with_no_cost_line_gives_nothing_and_no_error():
    server, g = game("TUPI")
    for u, name in (("k", "KING"), ("c", "TRADE_CART_EMPTY"), ("j", "JOAN_OF_ARC")):
        g.soldiers[u] = name
        server.entities[u] = {"Pos": (8.5, 64.0, 8.5)}
    train.census(g)
    for u in ("k", "c", "j"):
        del server.entities[u]
    train.census(g)
    assert set(g.stock.values()) == {0}
