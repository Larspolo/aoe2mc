"""game/bot.py: an unfinished site of the bot gets a new builder when its builder leaves (#1121). Fake server of
test_gather, the map of test_bot_gather."""
from test_bot_gather import bot_map

from game import bot


def builders(b, site):
    return [v for v in b.g.villagers.values() if v.site is site and v.state != "idle"]


def house(b):
    b.g.stock["wood"] = bot.build.price(b.g, "HOUSE")["wood"] + 5
    b.g.pop = 3                                                        # town center: limit 5
    b.step()
    site = b.g.sites[0]
    assert site["name"] == "HOUSE" and len(builders(b, site)) == 1
    return site


def test_a_site_whose_builder_went_to_a_resource_gets_a_new_builder():
    server, me, b = bot_map()
    site = house(b)
    v = builders(b, site)[0]
    b.go(v, "gold")                                                    # Gather.send: v.site = None
    assert v.site is None and builders(b, site) == []
    b.step()
    assert len(builders(b, site)) == 1 and len(b.g.sites) == 1        # a new builder, no second site
    for _ in range(3000):
        b.step()
        if site.get("done"):
            break
    assert site.get("done")


def test_an_idle_builder_goes_back_to_its_site():
    server, me, b = bot_map()
    site = house(b)
    v = builders(b, site)[0]
    b.g.set(v, "idle")                                                 # for example no path to the site
    b.step()
    assert builders(b, site) == [v]


def test_a_site_with_a_working_builder_gets_no_second_one():
    server, me, b = bot_map()
    site = house(b)
    for _ in range(5):
        b.step()
        assert len([v for v in b.g.villagers.values() if v.site is site]) == 1
