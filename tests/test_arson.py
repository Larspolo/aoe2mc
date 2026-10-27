"""game/train.py: the barracks researches Arson in the Feudal Age (75 food, 25 gold, 25 s, AoE2 DE wiki infobox):
the infantry of the player gets +2 attack against the standard buildings, not against walls, gates and the wonder,
and other units do not change (#1419)."""
import shutil
import time

import pytest
from test_forging import menus, setup

from game import civs, combat, run, train

BARRACKS = (17, 3)


def hit(a, t):
    """The melee damage of the Stats a against the Stats t: the rule of combat.damage and AoePlugin.java."""
    return max(1, max(0, a.attack - t.melee) + sum(a.bonus.get(c, 0) for c in t.classes))


def test_the_cost_time_and_age_are_those_of_aoe2():
    assert train.HELP["ARSON"] and "ARSON" in train.TRAINS["BARRACKS"]
    assert civs.MISSING["ARSON"] == ("GOTHS", "MUISCA", "ROMANS")             # the wiki availability


def test_the_barracks_menu_has_arson_in_the_feudal_age():
    server, g = setup(age=0)
    train.open_menu(g, "Steve", BARRACKS)
    assert "Arson" not in menus(server)[-1]
    server, g = setup()
    train.open_menu(g, "Steve", BARRACKS)
    assert " 6:book:Arson:75 food · 25 gold · 25 s · research " in menus(server)[-1] + " "


def test_the_standard_buildings_have_their_class_and_the_walls_not():
    assert combat.STANDARD in combat.stats("HOUSE").classes and combat.STANDARD in combat.stats("CASTLE").classes
    assert combat.STANDARD not in combat.stats("WONDER").classes
    assert combat.STANDARD not in combat.wall("STONE_WALL", 1).classes and combat.STANDARD not in combat.wall("GATE", 1).classes
    box, uuid = (8, 64, 8, 23, 104, 23), combat.target_uuid([8, 8, 24, 24])
    house, = [c for c in combat.building(uuid, "HOUSE", 1, box) if c.startswith("aoe building")]
    wall, = [c for c in combat.building(uuid, "STONE_WALL", 1, box, s=combat.wall("STONE_WALL", 1))
             if c.startswith("aoe building")]
    assert house == f"aoe building {uuid} 550 0 7 8 64 8 23 104 23"      # the default classes of the plugin
    assert wall == f"aoe building {uuid} 1080 8 10 8 64 8 23 104 23 building,stone"


def test_arson_gives_infantry_two_attack_against_standard_buildings():
    server, g = setup(food=75)
    g.stock["gold"] = 25
    rect = train.open_menu(g, "Steve", BARRACKS)
    slot = train.ITEMS["ARSON"][0]
    assert train.order(g, "Steve", rect, slot) == 1 and g.stock["food"] == 0 and g.stock["gold"] == 0
    server.log.clear()
    train.tick(g, 25)
    assert "ARSON" in g.techs and "Arson is researched." in " ".join(server.log)
    militia = train.stats(g, "MILITIA")
    house, wall = combat.stats("HOUSE"), combat.wall("STONE_WALL", 1)
    assert hit(militia, house) == hit(combat.stats("MILITIA"), house) + 2
    assert hit(militia, wall) == hit(combat.stats("MILITIA"), wall)
    assert hit(militia, combat.stats("ARCHER")) == hit(combat.stats("MILITIA"), combat.stats("ARCHER"))
    for name in ("SCOUT_CAVALRY", "ARCHER", "VILLAGER_MALE", "BATTERING_RAM"):
        assert train.stats(g, name) == combat.stats(name), name
    assert "aoe stats m 40 4 0 1 0 infantry standard:2 24" in server.log        # the live militia


@pytest.mark.mc
def test_an_arson_militia_hits_a_house_harder_than_a_wall_on_a_server(tiny_world, tmp_path):
    from test_building_damage import hp
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    militia = train.TECHS["ARSON"]("MILITIA", combat.stats("MILITIA"))
    with run.Game(world) as game:
        game.command("forceload add -2 -2 40 24")
        game.command(f"fill 0 {y - 1} 0 39 {y - 1} 21 stone_bricks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        targets = {}
        for name, x0, s in (("HOUSE", 8, None), ("STONE_WALL", 26, combat.wall("STONE_WALL", 1))):
            uuid = targets[name] = combat.target_uuid([x0, 8, x0 + 2, 10])
            for c in combat.building(uuid, name, 2, (x0, y, 8, x0 + 1, y + 3, 9), s=s):
                game.command(c)
            tag = name[0].lower()
            game.command(f'summon zombie {x0 - 1.5} {y} 8.5 {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p1 @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "MILITIA", militia)).strip() == "Stats: 1 units"
            assert game.command(f"aoe attack @e[tag={tag}] {uuid}").strip() == "Attack: 1 units"
        start, lost, end = {n: hp(game, u) for n, u in targets.items()}, {}, time.time() + 30
        while time.time() < end and len(lost) < 2:                     # the first hit on each target
            for n, u in targets.items():
                if n not in lost and hp(game, u) != start[n]:
                    lost[n] = start[n] - hp(game, u)
            time.sleep(0.05)
        # one hit: 4 attack - 0 melee armor + 2 (Arson) on a house; max(0, 4 - 8) = 0, at least 1, on a stone wall
        assert lost == {"HOUSE": 6, "STONE_WALL": 1}, lost
