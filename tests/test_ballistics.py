"""game/train.py and the Paper plugin: the university researches Ballistics in the Castle Age,
#1549. After it, the arrows of the own archers and buildings aim at the place where a moving target will
be when the arrow arrives (aoe ballistics)."""
import re
import shutil
import time

import pytest
from menu_line import item
from test_damage import health
from test_loom import menus
from test_tower_upgrades import research, setup

from game import combat, run, train


def text(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def test_the_university_menu_shows_ballistics_in_the_castle_age():
    for age, shown in ((1, False), (2, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (9, 9))
        assert (":book:Ballistics:" in menus(server)[-1]) == shown
    assert item(menus(server)[-1], "Ballistics").endswith(":Ballistics:" + text(g, "BALLISTICS") + "research")


def test_the_research_turns_on_the_aim_of_the_plugin_on_paper():
    for paper in (False, True):
        server, g = setup()
        g.paper = paper
        g.stock.update(wood=600, gold=600)
        research(g, "BALLISTICS")
        assert ("aoe ballistics p1 on" in server.log) == paper


@pytest.mark.mc
def test_a_tower_hits_a_walking_unit_more_often_with_ballistics(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                    # a floor in the air, inside the world border
    box = (20, y, 20, 23, y + 12, 23)          # a watch tower of 1 tile
    uuid = combat.target_uuid([20, 20, 24, 24])
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")      # zombies burn in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon zombie 42.5 {y} 6.5 {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')
        game.command("team join p2 @e[tag=e]")
        game.command("aoe stats @e[tag=e,limit=1] 10000 4 0 1 0 infantry - 20")   # pierce armor 1: 4 per arrow
        for c in combat.building(uuid, "WATCH_TOWER", 1, box):
            game.command(c)

        def hits(seconds):
            """The arrows that hit the enemy while it walks to and fro across the line of fire, 20 blocks away."""
            h0, end, k = health(game, "e"), time.time() + seconds, 0
            while time.time() < end:
                z = float(re.findall(r"(-?[\d.]+)d", game.command("data get entity @e[tag=e,limit=1] Pos"))[2])
                if k % 2 == 0 and z < 10 or k % 2 == 1 and z > 34:
                    game.command(f"aoe moveto @e[tag=e] 42.5 {y} {38.5 if k % 2 == 0 else 6.5}")
                    k += 1
                time.sleep(0.2)
            return round((h0 - health(game, "e")) / 4)

        without = hits(15)
        assert game.command("aoe ballistics p1 on").strip() == "Ballistics: [p1]"
        with_ = hits(15)
        assert with_ >= without + 4 and with_ >= 8, (without, with_)   # about 12 arrows in 15 s
