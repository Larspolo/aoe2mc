"""game/train.py, game/fleet.py and game/combat.py: an own dock trains the hulk in the Feudal Age with its AoE2 DE values
(wiki infobox "Hulk", The Last Chieftains), and a hulk sails next to an enemy ship (range 1) and attacks it with melee
damage (#1489). The first row of the dock menu is full: the hulk is in the third row, after the trade cog and the
cannon galleon (train.MORE + 2). Fake server."""
import math

from test_dock_train import DOCK, dock_map
from test_train_archery import menus

import units
from game import build, civs, combat, fleet, gather, train


def hulk(g):
    """A hulk of player 1 from the dock, in the Feudal Age."""
    g.techs = {"FEUDAL_AGE"}
    g.stock["gold"] = 100
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (15, 12)), train.MORE + 2) == 1
    uuid, = train.tick(g, 42)
    return uuid


def test_the_hulk_has_the_aoe2_de_values_of_the_wiki():
    assert train.COSTS["HULK"] == {"wood": 75, "gold": 35} and train.TRAIN_TIMES["HULK"] == 42
    assert build.AGE["HULK"] == 1 and "HULK" in train.TRAINS["DOCK"] and "HULK" not in civs.MISSING
    assert combat.stats("HULK") == (85, 4, 3, 1, 1, 1.75, {"fireship": 1, "standard": -3}, ("ship",))
    assert fleet.SPEEDS["HULK"] == 1.42 and combat.sight("HULK") == 5
    assert len(train.HELP["HULK"]) <= 50 and units.classify("HULK") == units.classify("GALLEY")   # an oak boat


def test_the_hulk_hits_with_melee_damage_more_vs_fire_ships_and_less_vs_buildings():
    assert combat.stats_command("u", "HULK").split()[7] == "2"                # ranged with melee damage
    assert combat.damage("HULK", "GALLEY") == 4 - 0                         # the melee armor of the galley
    assert combat.damage("HULK", "FIRE_GALLEY") == 4 - 1 + 1 and combat.damage("HULK", "FIRE_SHIP") == 4 - 2 + 1
    assert combat.damage("HULK", "DOCK") == max(1, 4 - combat.stats("DOCK").melee - 3)


def test_the_dock_menu_has_the_hulk_in_the_third_row_from_the_feudal_age():
    server, g = dock_map()
    train.open_menu(g, "Steve", (15, 12))
    assert f"{train.MORE + 2}:gray_dye:Hulk:75 wood · 35 gold · 42 s · Needs the Feudal Age" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, train.MORE + 2) == 0
    uuid = hulk(g)
    assert g.soldiers[uuid] == "HULK" and uuid in g.ships and (g.stock["wood"], g.stock["gold"]) == (125, 65)
    train.open_menu(g, "Steve", (15, 12))
    assert f"{train.MORE + 2}:oak_boat:Hulk:75 wood · 35 gold · 42 s · queue 0/15" in menus(server)[-1]


def test_a_click_in_the_queue_row_still_cancels_a_unit():
    server, g = dock_map()
    g.techs, g.stock["gold"] = {"FEUDAL_AGE"}, 100
    assert train.order(g, "Steve", DOCK, train.MORE + 2) == 1 and g.stock["wood"] == 125
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
