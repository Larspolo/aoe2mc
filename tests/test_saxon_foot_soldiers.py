"""Saxons (#2177, AoE2 DE wiki "Saxons"): foot soldiers cost a share less for each complete own town center or castle,
up to a most share (civs.COST_PER). Foot soldiers are the infantry: the knight and the units of other civilizations cost the
same as before."""
from test_hoardings import setup

from game import civs, train

(_, _, EACH, MOST), = civs.COST_PER["SAXONS"]                         # the share per building and the most share


def game(civ="SAXONS", town_centers=1, castles=0, sites=()):
    server, g = setup()
    g.data["players"]["1"]["civ"] = civ
    g.data["objects"] = [o for o in g.data["objects"] if o["kind"] != "building"] + \
        [{"kind": "building", "name": n, "player": 1, "tile": [0, 0]}
         for n in ["TOWN_CENTER"] * town_centers + ["CASTLE"] * castles]
    g.sites = [{"name": n, "player": 1, "done": done} for n, done in sites]
    return g


def less(g, name, share):
    return {r: int(v * (1 - share) + 0.5) for r, v in train.COSTS[name].items()}


def test_each_town_center_and_castle_gives_a_share_less_for_the_militia():
    assert train.price(game(), "MILITIA") == less(game(), "MILITIA", EACH)
    assert train.price(game(castles=1), "MILITIA") == less(game(), "MILITIA", min(2 * EACH, MOST))
    assert train.price(game(town_centers=0), "MILITIA") == train.COSTS["MILITIA"]


def test_the_share_has_a_most():
    g = game(town_centers=3, castles=2)
    assert train.price(g, "MILITIA") == less(g, "MILITIA", min(5 * EACH, MOST))
    assert train.price(game(town_centers=4, castles=4), "MILITIA") == less(g, "MILITIA", min(8 * EACH, MOST))


def test_only_a_complete_building_counts():
    g = game(sites=[("TOWN_CENTER", True), ("CASTLE", False)])
    assert train.price(g, "MILITIA") == less(g, "MILITIA", min(2 * EACH, MOST))


def test_a_knight_and_the_infantry_of_other_civilizations_cost_the_same():
    assert train.price(game(castles=1), "KNIGHT") == train.COSTS["KNIGHT"]
    assert train.price(game("BRITONS", castles=1), "MILITIA") == train.COSTS["MILITIA"]
