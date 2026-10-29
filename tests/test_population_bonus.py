"""game/train.py and game/civs.py: the population bonuses of the AoE2 DE wiki civilization pages (#2118): Chinese town
centers support more population and see farther, Goths have a higher population limit in the Imperial Age, Inca houses
support more population. The other civilizations keep the room of train.HOUSING and at most train.LIMIT. The values come
from the data: the tests compare with the Franks."""
from test_train_population import setup

from game import train

build = train.build
ROOM = train.HOUSING["TOWN_CENTER"] + 2 * train.HOUSING["HOUSE"]       # a town center and 2 houses


def player(civ, houses=2):
    server, g = setup(houses=houses)
    g.data["players"] = {"1": {"civ": civ}}
    return g


def test_a_chinese_town_center_supports_more():
    assert train.limit(player("CHINESE")) > train.limit(player("FRANKS")) == ROOM


def test_an_inca_house_supports_more():
    assert train.limit(player("INCAS")) > ROOM and train.limit(player("INCAS", houses=45)) == train.LIMIT


def test_the_goths_have_more_in_the_imperial_age():
    g = player("GOTHS", houses=45)
    assert train.max_pop(g) == train.limit(g) == train.LIMIT
    g.techs |= set(build.AGE_TECHS[:3])
    extra = train.max_pop(g) - train.LIMIT
    assert extra > 0 and train.limit(g) == train.max_pop(g)            # 46 buildings give more room
    f = player("FRANKS", houses=45)
    f.techs |= set(build.AGE_TECHS[:3])
    assert train.max_pop(f) == train.LIMIT
    g.pop_limit = 150                                                  # the setting of the game (#2266)
    assert train.max_pop(g) == 150 + extra


def test_a_chinese_town_center_sees_farther():
    chinese, franks = (player(c, houses=0).seen_tiles({}) for c in ("CHINESE", "FRANKS"))
    assert franks < chinese and max(x for x, _ in chinese) > max(x for x, _ in franks)
