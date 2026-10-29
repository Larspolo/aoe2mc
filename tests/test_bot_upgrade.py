"""game/bot.py: a bot upgrades the unit line of its soldiers (#3952). Fake server of test_gather, the map of
test_bot_gather."""
from test_bot_train import with_buildings

from game import bot

build, train = bot.build, bot.train                                   # the modules that bot uses


def feudal():
    server, me, b = with_buildings("HOUSE", "BARRACKS")
    b.villagers = len(b.g.villagers)
    b.g.techs.update(build.AGE_TECHS[:1])
    b.g.stock.update({r: 5000 for r in b.g.stock})
    return b


def queued(b):
    return [e["name"] for q in b.g.queues.values() for e in q]


def test_the_bot_queues_the_man_at_arms_upgrade():
    b = feudal()
    b.research()
    assert "MAN_AT_ARMS_UPGRADE" in queued(b)


def test_after_the_upgrade_the_bot_trains_men_at_arms():
    b = feudal()
    b.g.techs.add("MAN_AT_ARMS_UPGRADE")
    b.recruit()
    assert "MAN_AT_ARMS" in queued(b) and "MILITIA" not in queued(b)


def test_no_upgrade_in_the_dark_age():
    b = feudal()
    b.g.techs.difference_update(build.AGE_TECHS)
    b.research()
    assert "MAN_AT_ARMS_UPGRADE" not in queued(b)
