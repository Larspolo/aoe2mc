"""game/train.py and game/civs.py: the population bonuses of the AoE2 DE wiki civilization pages (#2118): Chinese town
centers support 15 population and see 7 tiles more, Goths have a population limit of 210 in the Imperial Age, Inca
houses support 10 population. The other civilizations keep 5 per house and town center and at most 200."""
from test_train_population import setup

from game import train

build = train.build


def player(civ, houses=2):
    server, g = setup(houses=houses)
    g.data["players"] = {"1": {"civ": civ}}
    return g


def test_a_chinese_town_center_supports_15():
    assert train.limit(player("CHINESE")) == 15 + 2 * 5 and train.limit(player("FRANKS")) == 3 * 5


def test_an_inca_house_supports_10():
    assert train.limit(player("INCAS")) == 5 + 2 * 10 and train.limit(player("INCAS", houses=45)) == 200


def test_the_goths_have_10_more_in_the_imperial_age():
    g = player("GOTHS", houses=45)
    assert train.max_pop(g) == train.limit(g) == 200
    g.techs |= set(build.AGE_TECHS[:3])
    assert train.max_pop(g) == train.limit(g) == 210                   # 46 buildings give 230
    f = player("FRANKS", houses=45)
    f.techs |= set(build.AGE_TECHS[:3])
    assert train.max_pop(f) == 200
    g.pop_limit = 150                                                  # the setting of the game (#2266): 160
    assert train.max_pop(g) == 160


def test_a_chinese_town_center_sees_7_tiles_more():
    chinese, franks = (player(c, houses=0).seen_tiles({}) for c in ("CHINESE", "FRANKS"))
    assert franks < chinese and max(x for x, _ in chinese) == max(x for x, _ in franks) + 7
