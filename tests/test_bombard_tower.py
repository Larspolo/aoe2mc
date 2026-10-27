"""Chemistry and the technology Bombard Tower at the university, and the bombard tower in the build menu (#1375):
the AoE2 DE values (wiki infoboxes "Chemistry_(Age_of_Empires_II)", "Bombard_Tower_(technology)", "Bombard_Tower").
Fake server."""
import math

from test_build_site import site_map

from game import build, civs, combat, garrison, train


def imperial(civ="TEUTONS", techs=()):
    server, g = site_map()
    g.data["players"]["1"]["civ"] = civ
    g.techs |= set(build.AGE_TECHS) | set(techs)
    return server, g


def test_the_university_has_chemistry_and_then_bombard_tower():
    assert (train.COSTS["CHEMISTRY"], train.TRAIN_TIMES["CHEMISTRY"], train.TECH_AGE["CHEMISTRY"]) \
        == ({"food": 300, "gold": 200}, 100, 3)
    assert (train.COSTS["BOMBARD_TOWER_TECH"], train.TRAIN_TIMES["BOMBARD_TOWER_TECH"]) == ({"food": 800, "wood": 400}, 60)
    u = train.TRAINS["UNIVERSITY"]
    assert u.index("BOMBARD_TOWER_TECH") == u.index("CHEMISTRY") + 1
    server, g = imperial()
    assert train.unlocked(g, "CHEMISTRY") and not train.unlocked(g, "BOMBARD_TOWER_TECH")   # after Chemistry
    g.techs.add("CHEMISTRY")
    assert train.unlocked(g, "BOMBARD_TOWER_TECH")
    server, g = imperial("BRITONS", ["CHEMISTRY"])                    # not of every civilization
    assert "BRITONS" in civs.MISSING["BOMBARD_TOWER_TECH"] and not train.unlocked(g, "BOMBARD_TOWER_TECH")
    assert not set(civs.MISSING["BOMBARD_TOWER_TECH"]) & {"TEUTONS", "TURKS", "SPANISH", "CHINESE", "KOREANS"}


def test_the_build_menu_has_the_bombard_tower_after_the_research():
    server, g = imperial(techs=["CHEMISTRY"])
    items = {name: (icon, lore) for _, icon, name, lore in build.items(g)}
    assert items["Bombard Tower"] == (build.LOCKED, "100 gold, 125 stone\n80 s\nNeeds Bombard Tower")
    g.techs.add("BOMBARD_TOWER_TECH")
    items = {name: (icon, lore) for _, icon, name, lore in build.items(g)}
    assert items["Bombard Tower"] == ("polished_basalt", "100 gold, 125 stone\n80 s")


def test_a_done_bombard_tower_shoots_with_the_aoe2_values_and_chemistry():
    assert combat.stats("BOMBARD_TOWER")[:6] == (2220, 120, 3, 9, 8, 6.0) and combat.MIN_RANGE.get("BOMBARD_TOWER", 1) == 1
    server, g = imperial(techs=["CHEMISTRY", "BOMBARD_TOWER_TECH"])
    g.stock.update(gold=100, stone=125)
    site = build.found(g, "BOMBARD_TOWER", (12, 13, 8, 9))
    assert (g.stock["gold"], g.stock["stone"]) == (0, 0)
    assert build.rise(g, site, math.inf)
    uuid = combat.target_uuid([12, 8, 13, 9])
    shot = next(c for c in server.log if c.startswith(f"aoe building {uuid} "))
    assert shot.startswith(f"aoe building {uuid} 2220 3 9 ") and shot.endswith(f" 121 8 {round(6.0 / 1.7 * 20)}")   # +1 Chemistry
    assert f"aoe arrows {uuid} 1" in server.log
    assert garrison.arrows("BOMBARD_TOWER", ["VILLAGER"] * 5) == 1    # one cannon ball, no arrows of a garrison
    assert train.stats(g, "ARCHER").attack == combat.stats("ARCHER").attack + 1   # Chemistry for the archers
