"""game/train.py, game/fleet.py and game/combat.py: an own dock trains the fire galley and the demolition raft in the
Feudal Age (#1481), the Feudal Age forms of the fire ship and the demolition ship (#1440), with their AoE2 DE values
(wiki infoboxes "Fire Galley (Age of Empires II)" and "Demolition Raft")."""
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

import units
from game import build, civs, combat, train


def test_the_two_ships_have_the_aoe2_de_values_of_the_wiki():
    assert build.AGE["FIRE_GALLEY"] == build.AGE["DEMOLITION_RAFT"]
    assert {"DANES", "KOREANS", "VIKINGS"} <= set(civs.MISSING["DEMOLITION_RAFT"]) == set(civs.MISSING["DEMOLITION_SHIP"])


def test_they_look_as_the_fire_ship_and_the_demolition_ship():
    assert units.classify("FIRE_GALLEY") == units.classify("FIRE_SHIP")              # a mangrove boat with a blaze
    assert units.classify("DEMOLITION_RAFT") == units.classify("DEMOLITION_SHIP")    # a bamboo raft with a creeper


def test_the_fire_galley_hits_often_with_melee_damage_and_the_raft_blasts():
    assert combat.damage("FIRE_GALLEY", "GALLEY") == 2 - 0 + 1               # melee armor 0, +1 vs. long-range warships
    assert combat.damage("FIRE_GALLEY", "DOCK") < combat.damage("FIRE_SHIP", "DOCK")   # no bonus vs. buildings (DE)
    assert combat.range_command("u", "FIRE_GALLEY", 4) == "aoe range u 10.0 3 0"
    assert combat.stats_command("u", "FIRE_GALLEY").split()[7] == "2"         # ranged with melee damage
    assert combat.damage("DEMOLITION_RAFT", "GALLEY") == 75 and combat.damage("DEMOLITION_RAFT", "DOCK") == 75 + 180
    assert combat.range_command("u", "DEMOLITION_RAFT", 4) == "aoe range u 4.0 1 10.0"   # next to it, 2.5 tiles of blast


def test_the_dock_trains_them_from_the_feudal_age():
    server, g = dock_map(wood=400)
    g.techs, g.stock["gold"] = set(), 200
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "6:gray_dye:Fire Galley:75 wood · 45 gold · 49 s · Needs the Feudal Age" in menu
    assert "7:gray_dye:Demolition Raft:45 wood · 80 gold · 45 s · Needs the Feudal Age" in menu
    assert train.order(g, "Steve", DOCK, 6) == 0
    g.techs = {"FEUDAL_AGE"}
    train.open_menu(g, "Steve", (15, 12))
    assert "6:mangrove_boat:Fire Galley:75 wood · 45 gold · 49 s · queue 0/15" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, 6) == 1 and train.order(g, "Steve", DOCK, 7) == 1
    fire, = train.tick(g, 49)
    demo, = train.tick(g, 45)
    assert (g.soldiers[fire], g.soldiers[demo]) == ("FIRE_GALLEY", "DEMOLITION_RAFT")
    assert fire in g.ships and demo in g.ships
    assert f"aoe range {demo} 1.0 1 2.5" in server.log                  # tile size 1: a blast of 2.5 blocks
