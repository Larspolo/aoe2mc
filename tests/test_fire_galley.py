"""game/train.py, game/fleet.py and game/combat.py: an own dock trains the fire galley and the demolition raft in the
Feudal Age (#1481), the Feudal Age forms of the fire ship and the demolition ship (#1440)."""
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

import units
from game import build, civs, combat, train


def entry(g, name, state, icon=None):
    """The menu item of name with its cost and time for the player of g."""
    slot, item, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {k}" for k, v in train.COSTS[name].items())
    return f"{slot}:{icon or item}:{label}:{cost} · {train.seconds(g, name):g} s · {state}"


def test_the_raft_has_the_age_and_the_civilizations_of_the_demolition_ship():
    assert build.AGE["FIRE_GALLEY"] == build.AGE["DEMOLITION_RAFT"]
    assert set(civs.MISSING["DEMOLITION_RAFT"]) == set(civs.MISSING["DEMOLITION_SHIP"])


def test_they_look_as_the_fire_ship_and_the_demolition_ship():
    assert units.classify("FIRE_GALLEY") == units.classify("FIRE_SHIP")              # a mangrove boat with a blaze
    assert units.classify("DEMOLITION_RAFT") == units.classify("DEMOLITION_SHIP")    # a bamboo raft with a creeper


def test_the_fire_galley_hits_with_melee_damage_and_the_raft_blasts():
    assert combat.damage("FIRE_GALLEY", "DOCK") < combat.damage("FIRE_SHIP", "DOCK")   # no bonus vs. buildings (DE)
    assert combat.stats_command("u", "FIRE_GALLEY").split()[7] == "2"         # ranged with melee damage
    assert combat.range_command("u", "DEMOLITION_RAFT", 4).split()[-1] == str(combat.BLAST["DEMOLITION_RAFT"] * 4)


def test_the_dock_trains_them_from_the_feudal_age():
    server, g = dock_map(wood=400)
    g.techs, g.stock["gold"] = set(), 200
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert entry(g, "FIRE_GALLEY", "Needs the Feudal Age", "gray_dye") in menu
    assert entry(g, "DEMOLITION_RAFT", "Needs the Feudal Age", "gray_dye") in menu
    fire_slot, raft_slot = train.ITEMS["FIRE_GALLEY"][0], train.ITEMS["DEMOLITION_RAFT"][0]
    assert train.order(g, "Steve", DOCK, fire_slot) == 0
    g.techs = {"FEUDAL_AGE"}
    train.open_menu(g, "Steve", (15, 12))
    assert entry(g, "FIRE_GALLEY", "queue 0/15") in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, fire_slot) == 1 and train.order(g, "Steve", DOCK, raft_slot) == 1
    fire, = train.tick(g, train.seconds(g, "FIRE_GALLEY"))
    demo, = train.tick(g, train.seconds(g, "DEMOLITION_RAFT"))
    assert (g.soldiers[fire], g.soldiers[demo]) == ("FIRE_GALLEY", "DEMOLITION_RAFT")
    assert fire in g.ships and demo in g.ships
    assert combat.range_command(demo, "DEMOLITION_RAFT", 1) in server.log   # tile size 1: the blast in blocks
