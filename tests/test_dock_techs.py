"""game/train.py: the university researches Careening in the Castle Age (100 food, 200 gold, 50 s) and Dry Dock after
it in the Imperial Age (200 food, 400 gold, 60 s), in one slot: each one gives the own ships +1 pierce armor (#1441, AoE2
DE wiki infoboxes; update 169123 moved both from the dock to the university, and Dry Dock gives no speed now). Fake
server, no Minecraft."""
from test_loom import menus
from test_tower_upgrades import setup

from game import civs, combat, fleet, train

GALLEY, SHIP = "00000000-0000-0000-0000-00000000aaaa", "00000000-0000-0000-0000-00000000bbbb"


def test_the_cost_time_age_and_slot_are_those_of_aoe2():
    assert train.BY_KEY["after"]["DRY_DOCK"] == "CAREENING" and train.ITEMS["DRY_DOCK"][0] == train.ITEMS["CAREENING"][0]
    assert {"CAREENING", "DRY_DOCK"} <= set(train.TRAINS["UNIVERSITY"])
    assert "ROMANS" in civs.MISSING["DRY_DOCK"] and "CAREENING" not in civs.MISSING


def test_the_university_menu_shows_careening_in_the_castle_age_and_then_dry_dock_in_the_imperial_age():
    slot = train.ITEMS["CAREENING"][0]
    server, g = setup(1)
    train.open_menu(g, "Steve", (9, 9))
    assert "Careening" not in menus(server)[-1]                        # the Feudal Age
    server, g = setup(2)
    train.open_menu(g, "Steve", (9, 9))
    assert f" {slot}:book:Careening:100 food · 200 gold · 50 s · research " in menus(server)[-1] + " "
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", (9, 9))
    assert "Dry Dock" not in menus(server)[-1]
    g.techs.add("CAREENING")
    train.open_menu(g, "Steve", (9, 9))
    assert f" {slot}:book:Dry Dock:200 food · 400 gold · 60 s · research " in menus(server)[-1] + " "


def test_each_research_gives_the_own_ships_1_pierce_armor():
    server, g = setup(3)
    g.stock.update(food=300, gold=600)
    g.soldiers.update({GALLEY: "GALLEY", SHIP: "TRANSPORT_SHIP"})
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    for tech, n in (("CAREENING", 1), ("DRY_DOCK", 2)):
        server.log.clear()
        assert train.order(g, "Steve", train.open_menu(g, "Steve", (9, 9)), train.ITEMS[tech][0]) == 1
        train.tick(g, train.TRAIN_TIMES[tech])
        assert tech in g.techs
        for name in ("GALLEY", "FIRE_SHIP", "DEMOLITION_SHIP", "FISHING_SHIP", "TRANSPORT_SHIP"):
            assert train.stats(g, name) == combat.stats(name)._replace(pierce=combat.stats(name).pierce + n)
        assert train.stats(g, "MILITIA") == combat.stats("MILITIA") and train.stats(g, "CASTLE") == combat.stats("CASTLE")
        assert combat.stats_command(GALLEY, "GALLEY", train.stats(g, "GALLEY")) in server.log   # the live ships
        assert combat.stats_command(SHIP, "TRANSPORT_SHIP", train.stats(g, "TRANSPORT_SHIP")) in server.log
    assert fleet.speed("GALLEY", 4) == 1.36 * 4                        # no speed change in AoE2 DE
