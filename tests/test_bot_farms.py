"""game/bot.py: the bot of player 2 builds farms when its food sources are empty (#1026). Fake server of test_gather,
the map of test_bot_gather."""
import math

from test_bot_gather import bot_map

from game import bot


def farms(b):
    return [s for s in b.g.sites if s["name"] == "FARM"]


def no_bushes(b):
    for t in b.g.map.bushes:
        b.g.map.bushes[t] = 0


def test_a_farm_when_the_food_runs_out():
    server, me, b = bot_map()
    b.g.pop = 1
    b.g.stock["wood"] = bot.build.price(b.g, "FARM")["wood"]
    b.step()
    assert farms(b) == []                                              # the fruit bush has food
    no_bushes(b)
    b.step()
    assert len(farms(b)) == 1 and b.g.stock["wood"] == 0


def test_one_farmer_on_each_farm_and_no_more_farms_than_food_villagers():
    server, me, b = bot_map()
    no_bushes(b)
    b.g.pop, b.g.aegis = 1, True                                       # instant building at the site
    for _ in range(3000):
        b.g.stock["wood"] = 60
        b.step()
        if b.g.farmers:
            break
    tile, u = next(iter(b.g.farmers.items()))
    v = b.g.villagers[u]
    assert v.tree == tile and v.res == "food" and v.state != "idle"
    for _ in range(300):
        b.g.stock["wood"] = 60
        b.step()
    live = [t for t, k in b.g.map.farms.items() if k > 0 and t in b.g.map.own_farms]   # an empty farm: a new one
    assert 0 < len(live) <= math.ceil(bot.SHARE["food"] * len(b.g.villagers))
    assert len(set(b.g.farmers.values())) == len(b.g.farmers)          # one farm for each farmer
