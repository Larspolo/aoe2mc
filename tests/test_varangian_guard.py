"""Varangian Guard (#2011): the barracks of the Byzantines, Danes, Saxons, Varangians and Vikings trains the Varangian
Guard from the Castle Age (slot 21: 65 food, 45 gold, 30 s) and researches Elite Varangian Guard in the Imperial Age
(slot 22: 750 food, 475 gold, 50 s), with the values of the AoE2 DE wiki infoboxes "Varangian Guard (Age of Empires II)"
and "Elite Varangian Guard". The upgrade turns the live guards into elite ones. The gold while it attacks is not here:
the game program has no gold income from combat."""
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

import units
from game import civs, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
OWN = ("BYZANTINES", "DANES", "SAXONS", "VARANGIANS", "VIKINGS")


def barracks(civ="VIKINGS", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["vg"] = "VARANGIAN_GUARD"
    g.game.entities.setdefault("vg", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    for unit in ("VARANGIAN_GUARD", "ELITE_VARANGIAN_GUARD"):
        assert len(train.HELP[unit]) <= 50
        assert units.classify(unit)["id"] == "minecraft:zombie"
    assert len(train.HELP["ELITE_VARANGIAN_GUARD_UPGRADE"]) <= 50
    for name in ("VARANGIAN_GUARD", "ELITE_VARANGIAN_GUARD", "ELITE_VARANGIAN_GUARD_UPGRADE"):
        assert not set(OWN) & set(civs.MISSING[name])
        assert set(civs.MISSING[name]) == {r["name"] for r in civs.ROWS} - set(OWN)


def test_a_viking_player_sees_it_at_the_barracks_and_a_franks_player_does_not():
    server, g = barracks(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", BARRACKS)
    assert ":gray_dye:Varangian Guard:65 food · 45 gold · 30 s · Needs the Castle Age" in menus(server)[-1]
    server, g = barracks("VIKINGS", CASTLE)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert " 21:zombie_spawn_egg:Varangian Guard:65 food · 45 gold · 30 s · queue 0/15 " in menu
    assert "Elite Varangian Guard" not in menu                         # the upgrade: the Imperial Age
    assert train.queue(g, "Steve", BARRACKS, "VARANGIAN_GUARD")
    for civ in ("FRANKS", "BRITONS"):
        server, g = barracks(civ, CASTLE)
        train.open_menu(g, "Steve", BARRACKS)
        assert "Varangian Guard" not in menus(server)[-1]
        assert train.queue(g, "Steve", BARRACKS, "VARANGIAN_GUARD") is None


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = barracks()
    train.open_menu(g, "Steve", BARRACKS)
    assert " 22:book:Elite Varangian Guard:750 food · 475 gold · 50 s · research " in menus(server)[-1] + " "
    research(g, BARRACKS, "ELITE_VARANGIAN_GUARD_UPGRADE")
    assert g.soldiers["vg"] == "ELITE_VARANGIAN_GUARD"
    assert "aoe stats vg 96 17 2 2 0 infantry - 24" in server.log      # 80 HP + 20 % of the Vikings (wiki: 96)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert " 21:zombie_spawn_egg:Elite Varangian Guard:65 food · 45 gold · 30 s · queue 0/15 " in menu
    assert ":Varangian Guard:" not in menu and "22:book" not in menu
    assert train.queue(g, "Steve", BARRACKS, "ELITE_VARANGIAN_GUARD")
    assert train.queue(g, "Steve", BARRACKS, "VARANGIAN_GUARD") is None
