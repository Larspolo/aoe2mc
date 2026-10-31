"""game/train.py: the university researches Heated Shot in the Castle Age (AoE2 DE wiki), #1548. The arrows of the own
towers, castles and docks get the "Additive increase" of the wiki table against ships. The plugin takes the bonus as
the last argument of `aoe building` (AoePlugin.java)."""
import shutil
import time

import pytest
from menu_line import item
from test_loom import menus
from test_tower_upgrades import MAP, research, setup, uuid

from game import build, combat, run, train


def hit(a, t):
    """combat.damage of a ranged attacker with the values a on the values t."""
    return max(1, max(0, a.attack - t.pierce) + sum(a.bonus.get(c, 0) for c in t.classes))


def test_the_university_menu_shows_it_in_the_castle_age():
    for age, shown in ((1, False), (2, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (9, 9))
        assert (item(menus(server)[-1], "Heated Shot") or "").endswith(" · research") == shown
    g.data["players"]["1"]["civ"] = "SPANISH"
    train.open_menu(g, "Steve", (9, 9))
    assert ":book:Heated Shot:" not in menus(server)[-1]


def test_the_arrows_of_the_towers_hit_ships_harder():
    _, g = setup(2)
    galley, militia = combat.stats("GALLEY"), combat.stats("MILITIA")
    names = ("WATCH_TOWER", "CASTLE", "DOCK")
    ship = {n: build.values(g, n).bonus.get("ship", 0) for n in names}
    before = hit(build.values(g, "WATCH_TOWER"), galley), hit(build.values(g, "WATCH_TOWER"), militia)
    g.techs |= {"GUARD_TOWER", "KEEP"}
    keep = build.values(g, "WATCH_TOWER").bonus.get("ship", 0)                # a keep without Heated Shot
    g.techs -= {"GUARD_TOWER", "KEEP"}
    g.techs.add("HEATED_SHOT")
    assert hit(build.values(g, "WATCH_TOWER"), galley) > before[0]
    assert hit(build.values(g, "WATCH_TOWER"), militia) == before[1]           # not against land units
    assert all(build.values(g, n).bonus["ship"] > ship[n] for n in names)
    g.techs |= {"GUARD_TOWER", "KEEP"}
    assert build.values(g, "WATCH_TOWER").bonus["ship"] > keep                 # the values of a keep
    assert build.values(g, "HOUSE") == combat.stats("HOUSE")


def test_the_research_gives_the_own_towers_the_bonus():
    server, g = setup(2)
    g.stock.update(food=1000, gold=1000)
    server.hp[uuid(MAP)] = 1000                                        # the tower lost 20 hit points
    research(g, "HEATED_SHOT")
    cmd, = [c for c in server.log if c.startswith(f"aoe building {uuid(MAP)} ")]
    s = build.values(g, "WATCH_TOWER")
    assert cmd.endswith(" " + ",".join(f"{c}:{n}" for c, n in sorted(s.bonus.items())))   # the bonus is the last argument
    assert server.hp[uuid(MAP)] == 1000


def test_a_building_without_a_bonus_keeps_its_short_command():
    s = combat.stats("TOWN_CENTER")._replace(bonus={"ship": 1})       # all buildings that shoot have a bonus (#1564)
    long, short = (combat.building(combat.target_uuid([2, 2, 6, 6]), "TOWN_CENTER", 1, (8, 64, 8, 23, 104, 23), s=t)[-1]
                   for t in (s, s._replace(bonus={})))
    assert long.endswith(" ship:1") and long.startswith(short + " ") and short.split()[-1].isdigit()


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
        assert cmds[-1].endswith(" building,standard,stone ship:6")
        for c in cmds:
            assert "Bad" not in game.command(c)
        end = time.time() + 20
        while health(game, "s") == 1000.0 and time.time() < end:
            time.sleep(0.2)
        time.sleep(3)                                                  # more arrows
        h = health(game, "s")
        assert h < 990 and (1000 - h) % 10 == 0, h
