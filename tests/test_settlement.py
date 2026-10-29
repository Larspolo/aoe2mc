"""game/build.py: the Incas, Mapuche, Muisca and Tupi build the Settlement in place of the mill, the lumber camp and the
mining camp (#2420, AoE2 DE wiki "Settlement (Age of Empires II)"): its footprint, its population, a drop site of all
resources, and the buildings that it counts for the Feudal Age."""
from test_folwark import complete, polish

import buildings
from game import train


def test_the_settlement_researches_the_technologies_of_the_mill_and_the_lumber_camp():
    assert set(train.TRAINS["MILL"]) | set(train.TRAINS["LUMBER_CAMP"]) <= set(train.TRAINS["SETTLEMENT"])


def test_a_settlement_takes_all_resources_and_gives_its_population():
    server, g = polish("TUPI")
    before = train.limit(g)
    site = complete(g, "SETTLEMENT", 20, 20)
    x0, x1, z0, z1 = site["footprint"]
    n = buildings.footprint("SETTLEMENT") * g.map.T
    assert (x1 - x0, z1 - z0) == (n, n)
    cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    assert all(cells in g.map.drops[r] for r in ("wood", "food", "gold", "stone"))
    assert train.limit(g) == before + train.HOUSING["SETTLEMENT"]


def test_a_settlement_counts_as_two_buildings_for_the_feudal_age():
    server, g = polish("MAPUCHE")
    assert train.missing(g, "FEUDAL_AGE").endswith(f"(0/{train.REQUIRES['FEUDAL_AGE'][0]})")
    complete(g, "SETTLEMENT", 20, 20)
    assert train.missing(g, "FEUDAL_AGE") is None
