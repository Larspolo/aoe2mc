"""game/build.py: the Incas, Mapuche, Muisca and Tupi build the Settlement in place of the mill, the lumber camp and the
mining camp (#2420, AoE2 DE wiki "Settlement (Age of Empires II)"): 125 wood, 40 s, the Dark Age, 1000 hit points,
0/7 armor, line of sight 6, 3 × 3 tiles, 5 population, a drop site of all resources, and two buildings for the Feudal
Age."""
from test_folwark import complete, polish
from test_krepost import shown

from game import build, civs, combat, train

CIVS = ("INCAS", "MAPUCHE", "MUISCA", "TUPI")


def test_the_values_of_the_wiki():
    assert "SETTLEMENT" not in build.AGE and train.HOUSING["SETTLEMENT"] == 5
    s = combat.BUILDINGS["SETTLEMENT"]
    assert (s.hp, s.attack, s.melee, s.pierce) == (1000, 0, 0, 7) and combat.SIGHT["SETTLEMENT"] == 6
    assert set(train.TRAINS["MILL"]) | set(train.TRAINS["LUMBER_CAMP"]) <= set(train.TRAINS["SETTLEMENT"])


def test_only_the_south_american_civilizations_have_the_settlement_and_no_camps():
    for civ in CIVS:
        assert civ not in civs.MISSING["SETTLEMENT"]
        assert all(civ in civs.MISSING[b] for b in ("LUMBER_CAMP", "MILL", "MINING_CAMP"))
    server, g = polish("BRITONS")
    build.open_menu(g, "Steve")
    assert "Mill" in shown(server) and "Settlement" not in shown(server)
    server, g = polish("INCAS")
    build.open_menu(g, "Steve")
    assert "Settlement" in shown(server) and not {"Mill", "Lumber Camp", "Mining Camp"} & set(shown(server))
    item = next(it for it in build.items(g) if it[2] == "Settlement")
    assert item[3] == "125 wood\n40 s"


def test_a_settlement_takes_all_resources_and_gives_5_population():
    server, g = polish("TUPI")
    before = train.limit(g)
    site = complete(g, "SETTLEMENT", 20, 20)
    x0, x1, z0, z1 = site["footprint"]
    assert (x1 - x0, z1 - z0) == (12, 12)                              # 3 × 3 tiles of 4 blocks
    cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    assert all(cells in g.map.drops[r] for r in ("wood", "food", "gold", "stone"))
    assert train.limit(g) == before + 5


def test_a_settlement_counts_as_two_buildings_for_the_feudal_age():
    server, g = polish("MAPUCHE")
    assert train.missing(g, "FEUDAL_AGE").endswith("(0/2)")
    complete(g, "SETTLEMENT", 20, 20)
    assert train.missing(g, "FEUDAL_AGE") is None
