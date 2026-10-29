"""game/train.py, game/fleet.py and game/combat.py: an own dock trains the hulk in the Feudal Age with its AoE2 DE values
(wiki infobox "Hulk", The Last Chieftains), and a hulk sails next to an enemy ship (range 1) and attacks it with melee
damage (#1489). The first row of the dock menu is full: the hulk is in the row under the queue row (train.MORE and
later). Fake server."""
import math

from menu_line import item
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

from game import combat, fleet, gather, train


def slot(server, g):
    """The slot of the hulk in the dock menu."""
    train.open_menu(g, "Steve", (15, 12))
    return int(item(menus(server)[-1], "Hulk").split(":")[0])


def hulk(g):
    """A hulk of player 1 from the dock, in the Feudal Age."""
    g.techs = {"FEUDAL_AGE"}
    g.stock["gold"] = 100
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (15, 12)), slot(g.game, g)) == 1
    uuid, = train.tick(g, train.seconds(g, "HULK", "DOCK"))
    return uuid


def test_the_hulk_hits_with_melee_damage_more_vs_fire_ships_and_less_vs_buildings():
    assert combat.stats_command("u", "HULK").split()[7] == "2"                # ranged with melee damage
    attack = combat.stats("HULK").attack
    assert combat.damage("HULK", "GALLEY") == attack - combat.stats("GALLEY").melee   # the melee armor of the galley
    for ship in ("FIRE_GALLEY", "FIRE_SHIP"):
        assert combat.damage("HULK", ship) > attack - combat.stats(ship).melee, ship   # a bonus
    assert combat.damage("HULK", "DOCK") < max(2, attack - combat.stats("DOCK").melee)


def test_the_dock_menu_has_the_hulk_in_the_third_row_from_the_feudal_age():
    server, g = dock_map()
    train.open_menu(g, "Steve", (15, 12))
    hull = item(menus(server)[-1], "Hulk")
    assert int(hull.split(":")[0]) >= train.MORE and hull.endswith(" · Needs the Feudal Age")
    assert train.order(g, "Steve", DOCK, slot(server, g)) == 0
    cost = train.price(g, "HULK")
    uuid = hulk(g)
    left = (200 - cost.get("wood", 0), 100 - cost.get("gold", 0))
    assert g.soldiers[uuid] == "HULK" and uuid in g.ships and (g.stock["wood"], g.stock["gold"]) == left
    train.open_menu(g, "Steve", (15, 12))
    assert item(menus(server)[-1], "Hulk").endswith(" · queue 0/15")


def test_a_click_in_the_queue_row_still_cancels_a_unit():
    server, g = dock_map()
    g.techs, g.stock["gold"] = {"FEUDAL_AGE"}, 100
    assert train.order(g, "Steve", DOCK, slot(server, g)) == 1 and g.stock["wood"] == 200 - train.price(g, "HULK")["wood"]
    assert train.order(g, "Steve", DOCK, train.ROW) == 0 and g.stock["wood"] == 200 and not g.queues.get(DOCK)


def test_a_hulk_sails_next_to_an_enemy_ship_and_attacks_it():
    server, g = dock_map()
    uuid = hulk(g)
    assert fleet.reach(g, "HULK") == 1                                  # tile size 1: next to the target
    server.entities["enemy"] = {"Pos": (21.5, 63.0, 2.5)}
    g.select(uuid)
    g.attack("enemy")
    assert f"aoe attack @e[tag={gather.SELECT}] enemy" in server.log
    v = g.ships[uuid]
    assert v.prey == "enemy" and v.path and math.dist(v.path[-1], (21, 2)) <= 1.5
    for _ in range(30):
        fleet.tick(g, 1.0)
    assert not v.path and math.dist(v.cell, (21, 2)) <= 1.5
