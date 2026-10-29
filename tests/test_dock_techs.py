"""game/train.py: the university researches Careening in the Castle Age and Dry Dock after it in the Imperial Age, in
one slot: each one gives the own ships its pierce armor (#1441; update 169123 moved both from the dock to the
university, and Dry Dock gives no speed now). Fake server, no Minecraft."""
from test_loom import menus
from test_tower_upgrades import setup

from game import combat, fleet, train

GALLEY, SHIP = "00000000-0000-0000-0000-00000000aaaa", "00000000-0000-0000-0000-00000000bbbb"


def price(tech):
    """The cost and time text of the menu line of tech."""
    return " · ".join([f"{v} {k}" for k, v in train.COSTS[tech].items()] + [f"{train.TRAIN_TIMES[tech]} s"])


def test_the_university_menu_shows_careening_in_the_castle_age_and_then_dry_dock_in_the_imperial_age():
    slot = train.ITEMS["CAREENING"][0]
    server, g = setup(1)
    train.open_menu(g, "Steve", (9, 9))
    assert "Careening" not in menus(server)[-1]                        # the Feudal Age
    server, g = setup(2)
    train.open_menu(g, "Steve", (9, 9))
    assert f" {slot}:book:Careening:{price('CAREENING')} · research " in menus(server)[-1] + " "
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", (9, 9))
    assert "Dry Dock" not in menus(server)[-1]
    g.techs.add("CAREENING")
    train.open_menu(g, "Steve", (9, 9))
    assert f" {slot}:book:Dry Dock:{price('DRY_DOCK')} · research " in menus(server)[-1] + " "


def test_each_research_gives_the_own_ships_1_pierce_armor():
    server, g = setup(3)
    g.stock.update(food=300, gold=600)
    g.soldiers.update({GALLEY: "GALLEY", SHIP: "TRANSPORT_SHIP"})
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    n, speed = 0, fleet.speed("GALLEY", 4)
    for tech in ("CAREENING", "DRY_DOCK"):
        n += next(r for r in train.ROWS if r["name"] == tech)["effect"]["add"]["pierce"]
        server.log.clear()
        assert train.order(g, "Steve", train.open_menu(g, "Steve", (9, 9)), train.ITEMS[tech][0]) == 1
        train.tick(g, train.TRAIN_TIMES[tech])
        assert tech in g.techs
        for name in ("GALLEY", "FIRE_SHIP", "DEMOLITION_SHIP", "FISHING_SHIP", "TRANSPORT_SHIP"):
            assert train.stats(g, name) == combat.stats(name)._replace(pierce=combat.stats(name).pierce + n)
        assert train.stats(g, "MILITIA") == combat.stats("MILITIA") and train.stats(g, "CASTLE") == combat.stats("CASTLE")
        assert combat.stats_command(GALLEY, "GALLEY", train.stats(g, "GALLEY")) in server.log   # the live ships
        assert combat.stats_command(SHIP, "TRANSPORT_SHIP", train.stats(g, "TRANSPORT_SHIP")) in server.log
    assert fleet.speed("GALLEY", 4) == speed                           # no speed change in AoE2 DE
