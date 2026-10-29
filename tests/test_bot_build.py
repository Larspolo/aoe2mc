"""game/bot.py: the bot of player 2 builds houses and the buildings of its build order (#857). Fake server of
test_gather, the map of test_bot_gather."""
from test_bot_gather import bot_map

from game import bot, build


def sites(b):
    return [s["name"] for s in b.g.sites]


def test_a_house_at_two_below_the_limit_with_one_builder():
    server, me, b = bot_map()
    b.g.stock["wood"] = build.price(b.g, "HOUSE")["wood"] + 5
    b.g.pop = 3                                                        # town center: limit 5
    b.step()
    assert sites(b) == ["HOUSE"] and b.g.stock["wood"] == 5
    site = b.g.sites[0]
    builders = [v for v in b.g.villagers.values() if v.site is site]
    assert len(builders) == 1 and builders[0].state in ("to_site", "build")
    assert build.free(b.g, site["footprint"]) is False                 # the foundation blocks its cells
    b.step()
    assert sites(b) == ["HOUSE"]                                       # one site at a time
    for _ in range(3000):
        b.step()
        if site.get("done"):
            break
    assert site.get("done") and builders[0].site is None


def test_no_house_below_the_gap():
    server, me, b = bot_map()
    b.g.stock["wood"] = 30
    b.g.pop = 2
    b.step()
    assert "HOUSE" not in sites(b)


def test_the_build_order_when_the_bot_has_the_resources():
    server, me, b = bot_map()
    b.g.pop = 1
    b.step()
    assert sites(b) == []                                              # no wood
    b.g.aegis = True                                                   # instant building at the site
    b.g.techs.update(bot.build.AGE_TECHS[:1])                          # the Feudal Age: the Blacksmith (#3951)
    for _ in range(3000):
        b.g.stock["wood"] = max(b.g.stock["wood"], 175)                # enough for each building
        b.step()
        if set(bot.ORDER) <= set(bot.train.owned(b.g)):
            break
    built = [n for n in sites(b) if n not in ("FARM", "HOUSE")]       # the census of 5 villagers asks for a house
    assert built == list(bot.ORDER)
    b.g.stock["wood"] = 1000
    for _ in range(50):
        b.step()
    assert [n for n in sites(b) if n not in ("FARM", "HOUSE")] == built   # each building once (farms: #1026)
    camp = next(s for s in b.g.sites if s["name"] == "LUMBER_CAMP")["footprint"]
    assert abs((camp[0] + camp[1]) / 2 - 26.5) + abs((camp[2] + camp[3]) / 2 - 21.5) < 6   # next to the trees
