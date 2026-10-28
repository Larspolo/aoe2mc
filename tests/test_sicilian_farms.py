"""game/train.py: the farm upgrades of the Sicilians give 125 % more food to each farm, as in AoE2 DE ("Farm upgrades
provide additional food +125%", #2230): Horse Collar adds 2.25 × 75 food to the live and the new own farms."""
from test_horse_collar import research, setup

from game import gather


def farm_food(civ):
    """The food of a live own farm and of a new farm before and after Horse Collar, for a player of civ."""
    _, g = setup()
    g.data["players"] = {"1": {"civ": civ, "color": "blue", "arch": "western"}}
    g.map.farms[(9, 9)] = 100
    new = g.map.farm_food
    research(g)
    return g.map.farms[(9, 9)] - 100, g.map.farm_food - new


def test_a_sicilian_farm_gets_125_percent_more_food():
    more = gather.FARM_TECHS["HORSE_COLLAR"]
    assert farm_food("SICILIANS") == (round(2.25 * more), round(2.25 * more))


def test_a_briton_farm_gets_the_normal_food():
    more = gather.FARM_TECHS["HORSE_COLLAR"]
    assert farm_food("BRITONS") == (more, more)
