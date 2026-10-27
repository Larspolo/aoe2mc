"""game/train.py: the university researches Heated Shot (350 food, 100 gold, 30 s) in the Castle Age (AoE2 DE wiki),
#1548. The arrows of the own towers, castles and docks get the "Additive increase" of the wiki table against ships:
a watch tower +6, a guard tower +9, a keep +10, a bombard tower +50, a castle and a dock +4. The plugin takes the bonus
as the last argument of `aoe building` (AoePlugin.java)."""
import shutil
import time

import pytest
from test_loom import menus
from test_tower_upgrades import MAP, research, setup, uuid

from game import build, civs, combat, run, train


def hit(a, t):
    """combat.damage of a ranged attacker with the values a on the values t."""
    return max(1, max(0, a.attack - t.pierce) + sum(a.bonus.get(c, 0) for c in t.classes))


def test_the_cost_time_age_and_civilizations_are_those_of_aoe2():
    assert train.COSTS["HEATED_SHOT"] == {"food": 350, "gold": 100} and train.TRAIN_TIMES["HEATED_SHOT"] == 30
    assert train.TECH_AGE["HEATED_SHOT"] == 2 and "HEATED_SHOT" in train.TRAINS["UNIVERSITY"]
    assert "SPANISH" in civs.MISSING["HEATED_SHOT"] and "BRITONS" not in civs.MISSING["HEATED_SHOT"]


def test_the_university_menu_shows_it_in_the_castle_age():
    for age, shown in ((1, False), (2, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (9, 9))
        assert (f" {train.MORE + 2}:book:Heated Shot:350 food · 100 gold · 30 s · research" in menus(server)[-1]) == shown
    g.data["players"]["1"]["civ"] = "SPANISH"
    train.open_menu(g, "Steve", (9, 9))
    assert ":book:Heated Shot:" not in menus(server)[-1]


def test_the_arrows_of_the_towers_hit_ships_harder():
    _, g = setup(2)
    galley = combat.stats("GALLEY")
    assert hit(build.values(g, "WATCH_TOWER"), galley) == 2             # 5 - 3 pierce armor
    g.techs.add("HEATED_SHOT")
    assert hit(build.values(g, "WATCH_TOWER"), galley) == 2 + 6
    assert hit(build.values(g, "WATCH_TOWER"), combat.stats("MILITIA")) == 5 - 1   # not against land units
    assert build.values(g, "CASTLE").bonus["ship"] == build.values(g, "DOCK").bonus["ship"] == 4
    g.techs |= {"GUARD_TOWER", "KEEP"}
    assert build.values(g, "WATCH_TOWER").bonus["ship"] == 10                     # the values of a keep
    assert build.values(g, "HOUSE") == combat.stats("HOUSE")


def test_the_research_gives_the_own_towers_the_bonus():
    server, g = setup(2)
    g.stock.update(food=1000, gold=1000)
    server.hp[uuid(MAP)] = 1000                                        # the tower lost 20 hit points
    research(g, "HEATED_SHOT", 30)
    cmd, = [c for c in server.log if c.startswith(f"aoe building {uuid(MAP)} ")]
    assert cmd.endswith(" 5 8 24 1 building,standard,stone ship:6")    # attack, range (T = 1), reload, min, classes, bonus
    assert server.hp[uuid(MAP)] == 1000


def test_a_building_without_a_bonus_keeps_its_short_command():
    tc = combat.building(combat.target_uuid([2, 2, 6, 6]), "TOWN_CENTER", 1, (8, 64, 8, 23, 104, 23))[-1]
    assert tc.endswith(" 5 24 24 0")


@pytest.mark.mc
def test_the_arrow_of_a_tower_with_heated_shot_hits_a_ship_harder_on_a_server(tiny_world, tmp_path):
    """The plugin reads the bonus of `aoe building`: 10 per arrow on a target of class ship (5 - 1 pierce armor + 6;
    without the bonus 4, tests/test_building_arrows.py)."""
    from test_damage import health
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    box = (20, y, 20, 23, y + 40, 23)                                  # a watch tower of 1 x 1 tiles (T = 4)
    uuid = combat.target_uuid([20, 20, 24, 24])
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")                              # zombies burn in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon zombie 36.5 {y} 21.5 {{NoAI:1b,IsBaby:0b,Tags:["s"]}}')   # 12 blocks from the tower
        game.command("team join p2 @e[tag=s]")
        assert game.command("aoe stats @e[tag=s,limit=1] 1000 4 0 1 0 ship - 20").strip() == "Stats: 1 units"
        s = combat.stats("WATCH_TOWER")
        cmds = combat.building(uuid, "WATCH_TOWER", 1, box, s=s._replace(bonus={"ship": 6}))
        assert cmds[-1].endswith(" building,standard ship:6")
        for c in cmds:
            assert "Bad" not in game.command(c)
        end = time.time() + 20
        while health(game, "s") == 1000.0 and time.time() < end:
            time.sleep(0.2)
        time.sleep(3)                                                  # more arrows
        h = health(game, "s")
        assert h < 990 and (1000 - h) % 10 == 0, h
