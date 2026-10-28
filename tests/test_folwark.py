"""game/build.py: a Polish player builds the Folwark in place of the mill (#1874, AoE2 DE wiki "Folwark (Age of Empires
II)"): 100 wood, 40 s, the Dark Age, 1000 hit points, 5 population, a food drop site with the mill technologies. A new
own farm with its whole footprint within 4 tiles of the Folwark gives 10 % of its food at once (18 food)."""
from test_build_site import Server
from test_gather import grid
from test_krepost import shown

from game import build, civs, combat, gather, train

DOWN = (0.0, 90.0)


def polish(civ="POLES"):
    """A flat 96 × 96 block map (tile size 4) with a villager of player 1 of civ."""
    data = grid([[64] * 96 for _ in range(96)], [])
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"civ": civ, "color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (30.5, 64.0, 30.5)}})
    g = gather.Gather(server, data).setup()
    g.stock.update(wood=1000)
    return server, g


def complete(g, name, x, z):
    """A complete site of name of player 1 at block (x, z)."""
    site = build.place(g, "Steve", name, (x + 0.5, g.map.y(x, z) + 10, z + 0.5), gather.direction(*DOWN))
    assert site and build.rise(g, site, build.BUILD_TIMES[name])
    return site


def test_the_values_of_the_wiki():
    assert build.BUILD_TIMES["FOLWARK"] == 40
    assert "FOLWARK" not in build.AGE and train.HOUSING["FOLWARK"] == 5
    s = combat.BUILDINGS["FOLWARK"]
    assert (s.hp, s.attack, s.melee, s.pierce) == (1000, 0, 0, 7) and combat.SIGHT["FOLWARK"] == 6
    assert train.TRAINS["FOLWARK"] == train.TRAINS["MILL"] and "HORSE_COLLAR" in train.TRAINS["FOLWARK"]
    assert civs.MISSING["MILL"] == ("POLES",) and "POLES" not in civs.MISSING["FOLWARK"]
    assert {"BRITONS", "FRANKS", "LITHUANIANS"} <= set(civs.MISSING["FOLWARK"])


def test_only_a_polish_player_has_the_folwark_and_no_mill_in_the_menu():
    server, g = polish("BRITONS")
    build.open_menu(g, "Steve")
    assert "Mill" in shown(server) and "Folwark" not in shown(server)
    server, g = polish()
    build.open_menu(g, "Steve")
    assert "Folwark" in shown(server) and "Mill" not in shown(server)
    folwark = next(it for it in build.items(g) if it[2] == "Folwark")
    assert folwark[0] == build.MENU.index("FOLWARK") and folwark[3] == "100 wood\n40 s"


def test_a_folwark_is_a_food_drop_site_and_gives_5_population():
    server, g = polish()
    before = train.limit(g)
    site = complete(g, "FOLWARK", 20, 20)
    x0, x1, z0, z1 = site["footprint"]
    assert {(x, z) for x in range(x0, x1) for z in range(z0, z1)} in g.map.drops["food"]
    assert train.limit(g) == before + 5


def test_a_new_farm_next_to_a_folwark_gives_18_food_at_once():
    server, g = polish()
    complete(g, "FOLWARK", 20, 20)
    food = g.stock["food"]
    farm = complete(g, "FARM", 36, 20)                                 # beside the Folwark
    tile = (farm["footprint"][0] // 4 + 1, farm["footprint"][2] // 4 + 1)
    assert g.stock["food"] == food + 18 and g.map.farms[tile] == gather.FARM_FOOD - 18
    far = complete(g, "FARM", 84, 84)                                  # more than 4 tiles away: no food
    assert g.stock["food"] == food + 18 and g.map.farms[(far["footprint"][0] // 4 + 1, far["footprint"][2] // 4 + 1)] \
        == gather.FARM_FOOD


def test_a_folwark_counts_as_the_mill_for_the_feudal_age():
    server, g = polish()
    assert train.missing(g, "FEUDAL_AGE").endswith("(0/2)")
    complete(g, "FOLWARK", 20, 20)
    assert train.missing(g, "FEUDAL_AGE").endswith("(1/2)")
