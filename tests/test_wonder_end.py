"""The wonder boss bars go when the game ends (#1178): the check of #1138 saw "1 year left" after the Victory."""
from test_cheat_end import cheat
from test_wonder import start, tick

from game import combat, wonder  # noqa: F401 (combat puts game/ on sys.path)


def test_the_bar_goes_at_the_end_of_the_countdown():
    server, g, _, _ = start()
    tick(g, wonder.years(g.data.get("map_size")) * wonder.YEAR)
    assert g.ended == "Victory"
    assert "bossbar remove aoe2mc:wonder_p1" in server.log


def test_the_bar_goes_when_a_cheat_ends_the_game():
    server, g, _, _ = start()
    tick(g, 100)
    assert "bossbar remove aoe2mc:wonder_p1" in cheat(server, g, "resign")
    assert g.ended == "Defeat"
