"""Chemistry and the technology Bombard Tower at the university, and the bombard tower in the build menu (#1375).
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
    server, g = imperial()
    assert train.unlocked(g, "CHEMISTRY") and not train.unlocked(g, "BOMBARD_TOWER_TECH")   # after Chemistry
    g.techs.add("CHEMISTRY")
    assert train.unlocked(g, "BOMBARD_TOWER_TECH")
    server, g = imperial(civs.MISSING["BOMBARD_TOWER_TECH"][0], ["CHEMISTRY"])   # not of every civilization
    assert not train.unlocked(g, "BOMBARD_TOWER_TECH")


def test_the_build_menu_has_the_bombard_tower_after_the_research():
    server, g = imperial(techs=["CHEMISTRY"])
    locked = {name: (icon, lore) for _, icon, name, lore in build.items(g)}["Bombard Tower"]
    g.techs.add("BOMBARD_TOWER_TECH")
    icon, lore = {name: (icon, lore) for _, icon, name, lore in build.items(g)}["Bombard Tower"]
    assert icon != build.LOCKED and locked == (build.LOCKED, lore + "\nNeeds Bombard Tower")


def test_a_done_bombard_tower_shoots_with_the_aoe2_values_and_chemistry():
    server, g = imperial(techs=["CHEMISTRY", "BOMBARD_TOWER_TECH"])
    cost = build.price(g, "BOMBARD_TOWER")
    g.stock.update(cost)
    site = build.found(g, "BOMBARD_TOWER", (12, 13, 8, 9))
    assert not any(g.stock[r] for r in cost)
    assert build.rise(g, site, math.inf)
    uuid = combat.target_uuid([12, 8, 13, 9])
    shot = next(c for c in server.log if c.startswith(f"aoe building {uuid} "))
    s = build.values(g, "BOMBARD_TOWER")
    assert s.attack > combat.stats("BOMBARD_TOWER").attack                           # Chemistry
    assert shot.startswith(f"aoe building {uuid} {s.hp} {s.melee} {s.pierce} ") and f" {s.attack} {s.range * g.map.T} " in shot
    assert f"aoe arrows {uuid} 1" in server.log
    assert garrison.arrows("BOMBARD_TOWER", ["VILLAGER"] * 5) == 1    # one cannon ball, no arrows of a garrison
    assert train.stats(g, "ARCHER").attack > combat.stats("ARCHER").attack       # Chemistry for the archers
