"""game/bot.py: a bot researches the economy technologies of its age (#3950). Fake server of test_gather, the map of
test_bot_gather."""
from test_bot_gather import bot_map

from game import bot

build, train = bot.build, bot.train                                   # the modules that bot uses


def ready(age=1):
    """A bot with its villager number, a lumber camp, and much of each resource in the given age."""
    server, me, b = bot_map()
    b.villagers = len(b.g.villagers)
    b.g.techs.update(build.AGE_TECHS[:age])
    b.g.stock.update({r: 5000 for r in b.g.stock})
    b.g.sites.append({"name": "LUMBER_CAMP", "player": 2, "footprint": [26, 28, 20, 22], "done": True})
    return b


def queued(b, building="LUMBER_CAMP"):
    return [e["name"] for rect, q in b.g.queues.items() if train.homes(b.g).get(rect) == building
            for e in q if e["name"] in train.TECHS]


def test_the_bot_researches_double_bit_axe_at_the_lumber_camp():
    b = ready(age=2)
    b.research()
    assert queued(b) == ["DOUBLE_BIT_AXE"]
    b.research()
    assert queued(b) == ["DOUBLE_BIT_AXE"]                             # one technology in the queue


def test_no_research_without_the_cost():
    b = ready(age=2)
    b.g.stock.update({r: 0 for r in b.g.stock})
    b.research()
    assert queued(b) == []


def test_no_double_bit_axe_in_the_dark_age():
    b = ready(age=0)
    b.research()
    assert "DOUBLE_BIT_AXE" not in queued(b)
