"""game/bot.py: the bot builds houses up to the population setting, not up to the AoE2 limit of 200 (#3108)."""
from test_bot_gather import bot_map

from game import train


def test_no_house_at_the_population_setting():
    server, me, b = bot_map()
    b.g.pop_limit = 25
    b.g.aegis = True
    seen, at_limit = set(), False
    for _ in range(400):
        b.g.stock["wood"] = 300
        b.g.pop = train.limit(b.g)
        b.step()
        houses = {id(s) for s in b.g.sites if s["name"] == "HOUSE"}
        if train.limit(b.g) == 25:
            assert houses <= seen                                       # no new house at the limit
            at_limit = True
        seen |= houses
    assert at_limit and train.limit(b.g) == 25
    assert any(s["name"] != "HOUSE" for s in b.g.sites)                 # a farm or a building of ORDER instead


def test_a_house_above_200_with_a_setting_of_500(monkeypatch):
    server, me, b = bot_map()
    b.g.pop_limit = 500
    b.g.stock["wood"] = 300
    monkeypatch.setattr(train, "limit", lambda g: 200)                 # a housing of 200 (the AoE2 limit)
    b.g.pop = 200
    b.step()
    assert any(s["name"] == "HOUSE" for s in b.g.sites)
