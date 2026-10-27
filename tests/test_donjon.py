"""game/build.py: a Sicilian player builds the Donjon; it shoots and trains the Serjeant and the spearman line (#1873).
Fake server."""
from test_build_menu import villager_map
from test_build_site import Server
from test_gather import grid
from test_krepost import DOWN, shown

from game import build, combat, garrison, gather, train


def test_only_a_sicilian_player_has_the_donjon_in_the_menu():
    server, g = villager_map()                                         # Britons
    build.open_menu(g, "Steve")
    assert "Donjon" not in shown(server)
    server.chosen = build.MENU.index("DONJON") + 1                     # also not with /trigger
    assert build.chosen(g, "Steve") is None
    g.data["players"]["1"]["civ"] = "SICILIANS"
    build.open_menu(g, "Steve")
    assert "Donjon" in shown(server) and "Krepost" not in shown(server)
    donjon = next(it for it in build.items(g) if it[2] == "Donjon")
    assert donjon[0] == build.MENU.index("DONJON") and donjon[3] == "50 wood, 175 stone\n83 s"   # the Dark Age
    assert build.chosen(g, "Steve") == "DONJON"


def test_the_values_of_the_wiki():
    s = combat.BUILDINGS["DONJON"]                                     # the Feudal Age
    assert (s.hp, s.attack, s.melee, s.pierce, s.range, s.reload) == (1250, 5, 1, 7, 8, 2.0)
    assert s.bonus == {combat.SHIP: 6} and s.classes == ("building", combat.STANDARD, combat.STONE)
    assert combat.FORT_MIN_RANGE["DONJON"] == 1 and combat.SIGHT["DONJON"] == 10
    assert garrison.SIZES["DONJON"] == 10 and "DONJON" not in build.AGE


def test_a_complete_donjon_shoots_and_trains_the_serjeant_and_the_spearman_line():
    data = grid([[64] * 48 for _ in range(48)], [])
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"civ": "SICILIANS", "color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (30.5, 64.0, 30.5)}},
                    chosen=build.MENU.index("DONJON") + 1)
    g = gather.Gather(server, data, carry=5, chop=0.25).setup()
    g.stock.update(wood=100, stone=200)
    g.click("Steve")
    site, = g.sites
    assert (g.stock["wood"], g.stock["stone"]) == (50, 25)
    g.select("v0")
    g.click("Steve")
    for _ in range(6000):
        g.step()
        if site["progress"] == 1:
            break
    assert site["progress"] == 1
    shot = [c for c in server.log if c.startswith("aoe building ") and " 5 " in c]
    assert shot, [c for c in server.log if c.startswith("aoe building")]
    rect = next(r for r, n in train.homes(g).items() if n == "DONJON")
    assert train.trains(g, "DONJON") == ("SERJEANT", "SPEARMAN", "ELITE_SERJEANT_UPGRADE")
    g.techs |= {"PIKEMAN_UPGRADE", "ELITE_SERJEANT_UPGRADE"}
    assert train.trains(g, train.homes(g)[rect])[:2] == ("ELITE_SERJEANT", "PIKEMAN")
