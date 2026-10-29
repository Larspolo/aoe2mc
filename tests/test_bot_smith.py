"""game/bot.py: a bot researches the Blacksmith technologies of its soldiers (#3951). Fake server of test_gather, the
map of test_bot_gather."""
from test_bot_research import queued, ready


def smith(soldiers, age=2):
    """A bot of the given age with a Blacksmith, much of each resource and the given soldiers."""
    b = ready(age=age)
    b.g.sites.append({"name": "BLACKSMITH", "player": 2, "footprint": [14, 17, 24, 27], "done": True})
    b.g.soldiers.update({f"s{i}": n for i, n in enumerate(soldiers)})
    return b


def test_the_bot_researches_fletching_for_its_archers():
    b = smith(["ARCHER", "ARCHER"])
    b.research()
    assert queued(b, "BLACKSMITH") == ["FLETCHING"]


def test_the_bot_researches_forging_for_its_infantry():
    b = smith(["MILITIA"])
    b.research()
    assert queued(b, "BLACKSMITH") == ["FORGING"]


def test_no_blacksmith_technology_without_soldiers():
    b = smith([])
    b.research()
    assert queued(b, "BLACKSMITH") == []
