"""game/bot.py: a bot with its villagers keeps the cost of the next age; soldiers and technologies take only the
resources above it (#4087)."""
from test_bot_train import with_buildings

from game import bot

build, train = bot.build, bot.train


def ready(monkeypatch, done=bot.ORDER):
    """A bot with its villager number, a barracks, the buildings of done and 560 food."""
    server, me, b = with_buildings("HOUSE", "BARRACKS")
    b.villagers = len(b.g.villagers)
    real = train.owned
    monkeypatch.setattr(train, "owned", lambda g: real(g) + list(done))
    b.g.stock.update(food=560, wood=0, gold=500, stone=0)
    return b


def ages(b):
    return [e["name"] for q in b.g.queues.values() for e in q if e["name"] in build.AGE_TECHS]


def test_the_bot_keeps_the_food_of_the_feudal_age(monkeypatch):
    b = ready(monkeypatch)
    age = build.AGE_TECHS[0]
    assert b.keep() == train.price(b.g, age, "TOWN_CENTER")
    for _ in range(3):
        b.recruit()
        b.research()
    assert b.g.stock["food"] >= b.keep()["food"]
    b.age_up()
    assert ages(b) == [age]
    assert b.keep() == {}                                              # queued: nothing more to keep


def test_with_the_age_in_the_queue_soldiers_take_the_food(monkeypatch):
    b = ready(monkeypatch)
    b.g.stock["food"] = 1060
    b.age_up()
    assert ages(b) == [build.AGE_TECHS[0]] and b.keep() == {}
    b.recruit()
    assert b.g.stock["food"] < 500                                     # nothing to keep: soldiers take the food


def test_the_bot_keeps_the_cost_of_a_missing_building_of_its_order(monkeypatch):
    first = next(n for n in bot.ORDER if n != "BARRACKS")
    b = ready(monkeypatch, [n for n in bot.ORDER if n != first])
    assert not build.locked(b.g, first) and b.keep() == build.price(b.g, first)
    b.age_up()
    assert ages(b) == []


def test_the_order_has_the_buildings_that_the_castle_age_needs():
    k, names = train.REQUIRES["CASTLE_AGE"][:2]                       # 2 of the Feudal Age buildings
    assert len(set(bot.ORDER) & set(names)) >= k
