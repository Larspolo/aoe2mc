"""game/bot.py: a bot queues the next age at its town center (#3912). Fake server of test_gather, the map of
test_bot_gather."""
from test_bot_gather import bot_map

from game import bot

build, train = bot.build, bot.train                                   # the modules that bot uses


def ready(monkeypatch, done=bot.ORDER):
    """A bot with its villager number, the buildings done and much of each resource."""
    server, me, b = bot_map()
    b.villagers = len(b.g.villagers)
    real = train.owned
    monkeypatch.setattr(train, "owned", lambda g: real(g) + list(done))
    b.g.stock.update({r: 5000 for r in b.g.stock})
    return b


def queued(b):
    return [e["name"] for q in b.g.queues.values() for e in q if e["name"] in build.AGE_TECHS]


def test_the_bot_queues_the_feudal_age(monkeypatch):
    b = ready(monkeypatch)
    b.age_up()
    assert queued(b) == [build.AGE_TECHS[0]]
    b.age_up()
    assert queued(b) == [build.AGE_TECHS[0]]                           # once


def test_no_age_without_the_resources_or_a_building(monkeypatch):
    b = ready(monkeypatch)
    b.g.stock.update({r: 0 for r in b.g.stock})
    b.age_up()
    assert queued(b) == []
    first = next(n for n in bot.ORDER if not build.locked(b.g, n))
    monkeypatch.undo()
    b = ready(monkeypatch, [n for n in bot.ORDER if n != first])
    b.age_up()
    assert queued(b) == []


def test_no_age_with_too_few_villagers(monkeypatch):
    b = ready(monkeypatch)
    b.villagers += 1
    b.age_up()
    assert queued(b) == []


def test_no_age_above_the_end_age(monkeypatch):
    b = ready(monkeypatch)
    b.g.data["end_age"] = 0
    b.age_up()
    assert queued(b) == []
