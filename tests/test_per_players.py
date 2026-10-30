"""game/per.py: the facts of the other players and the -total counts (#4572). The map of test_bot_gather: player 1
(a person) and the bot, player 2; they are enemies (no team)."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # the modules that per uses


def script(text=""):
    server, me, b = bot_map()
    me.bots = [b]                                                      # run.py: player 1 holds the bots
    return per.Script(per.parse(text), b), b, me


def test_military_population_of_the_enemy_sets_a_goal():
    for soldiers, goal in ((3, None), (4, 1)):
        s, b, me = script("(defrule (players-military-population any-enemy > 3) => (set-goal 1 1))")
        me.soldiers.update({f"s{i}": "MILITIA" for i in range(soldiers)})
        s.step()
        assert s.goals.get(1) == goal


def test_the_player_parameters():
    s, b, me = script()
    me.pop = 7
    assert s.check(("players-population", 1, "==", 7)) and s.check(("players-population", "every-enemy", ">", 6))
    assert s.check(("players-population", "focus-player", "==", 7)) and s.check(("players-population", "any-human", "==", 7))
    assert not s.check(("players-population", "any-ally", ">=", 0))    # the bot has no ally
    assert not s.check(("players-population", "any-computer", ">=", 0))
    assert s.check(("players-current-age", "any-enemy", "==", "dark-age"))
    me.techs.add(build.AGE_TECHS[0])
    assert s.check(("players-current-age", "any-enemy", ">=", "feudal-age"))
    assert s.check(("players-building-type-count", "any-enemy", "town-center", "==", 1))
    assert not s.check(("players-building-type-count", "any-enemy", "town-center", ">", 1))


def test_enemy_buildings_in_town():
    s, b, me = script()
    assert s.check(("enemy-buildings-in-town",))                       # the other town center is 18 tiles away
    per.TOWN, old = 17, per.TOWN
    try:
        assert not s.check(("enemy-buildings-in-town",))
    finally:
        per.TOWN = old
    me.data["objects"] = [o for o in me.data["objects"] if o.get("player") != 1]
    b.g.data["objects"] = me.data["objects"]
    me.sites.append({"name": "HOUSE", "player": 1, "footprint": [18, 19, 18, 19], "progress": 0.5})
    assert s.check(("enemy-buildings-in-town",))                       # a site of the enemy near the own town center


def test_total_counts_count_the_queue_and_the_sites():
    s, b, me = script()
    n = len(b.g.villagers)
    b.g.stock.update(food=1000)
    tc = next(c for c in s.homes("VILLAGER_MALE"))
    assert train.queue(b.g, b.nobody, tc, "VILLAGER_MALE")
    assert s.check(("unit-type-count-total", "villager", "==", n + 1)) and s.check(("unit-type-count", "villager", "==", n))
    b.g.sites.append({"name": "HOUSE", "player": 2, "footprint": [10, 11, 10, 11], "progress": 0.1})
    assert s.check(("building-type-count-total", "house", "==", 1)) and s.check(("building-type-count", "house", "==", 0))
