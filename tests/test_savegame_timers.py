"""A saved game of the game program keeps the wonder and relic victory timers and the market prices (#2324, epic
#2253): after a load a wonder timer goes on with its years left, and the market trades at the saved prices."""
import json

from test_loom import setup

from game import market, savegame, wonder


def played():
    """A wonder timer at 300 game seconds left (and one destroyed wonder), a relic timer and changed market prices."""
    server, g = setup()
    g.wonders = {"w1": {"player": 1, "left": 300.0}}
    g.wonders_gone = {"w0"}
    g.wonder_shown = {1: 1}
    g.relic_timer = {"player": 1, "left": 1200.0, "shown": 3}
    market.rates(g)["wood"] += 30
    return g


def loaded(g):
    _, h = setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return h


def test_a_loaded_game_has_the_timers_and_prices():
    g = played()
    h = loaded(g)
    assert h.wonders == g.wonders and h.wonders["w1"]["left"] == 300.0
    assert h.wonders_gone == {"w0"} and h.wonder_shown == {1: 1}
    assert h.relic_timer == g.relic_timer
    assert market.rates(h) == market.rates(g) and market.price(h, "wood", True) == market.price(g, "wood", True)


def test_the_wonder_timer_goes_on_after_the_load():
    h = loaded(played())
    h.wonder_at = float("inf")                                       # no entity check of the fake server
    wonder.tick(h, 10)
    assert h.wonders["w1"]["left"] == 290.0


def test_a_game_without_timers_gives_no_new_keys():
    _, g = setup()
    d = savegame.dump(g)
    assert not set(savegame.OPTIONAL) & set(d["players"]["1"])
    h = loaded(g)
    assert not set(savegame.OPTIONAL) & set(vars(h))
