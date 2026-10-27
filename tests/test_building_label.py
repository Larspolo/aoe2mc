"""The name line of a hurt building shows on a text display over its roof (#1811): the client draws no name of an
invisible mob for a player who is not a spectator, and the target of a building is an invisible slime (#636, #1538).
AoePlugin.label shows it while the building is hurt or selected, follows each hit and repair, and goes when it falls."""
import re
import shutil
import time

import pytest

from game import combat

LABEL = "@e[type=text_display,tag=aoe2mc.label]"


def label(game):
    """(red hearts, gray hearts, y) of the text display over the roof, or None."""
    if "passed" not in game.command(f"execute if entity {LABEL}"):
        return None
    one = f"{LABEL[:-1]},limit=1]"
    assert "House" in game.command(f"data get entity {one} text.extra[0]")
    red, gray = (game.command(f"data get entity {one} text.extra[{i}].text").rsplit(":", 1)[1].count("❤") for i in (2, 3))
    y = float(re.findall(r"-?[\d.]+", game.command(f"data get entity {one} Pos[1]").rsplit(":", 1)[1])[0])
    return red, gray, y


@pytest.mark.mc
def test_a_hurt_house_shows_its_hearts_over_the_roof(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, box = 200, (8, 200, 8, 13, 206, 13)                             # a house in the air, as test_health_display
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command(f"fill 0 {y - 1} 0 21 {y - 1} 21 stone_bricks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        uuid = combat.target_uuid([8, 8, 14, 14])
        for c in combat.building(uuid, "HOUSE", 2, box):
            game.command(c)
        assert game.command(combat.label_command(uuid, "HOUSE")).strip() == "Label: 1 units"
        assert label(game) is None                                     # full hit points, not selected
        game.command(f"scoreboard players set {uuid} aoe_hp 300")       # 300 of 550: 3 hearts
        game.command(f"aoe label {uuid}")
        assert label(game) == (3, 2, 208.5)                            # two blocks over the top of the box
        assert not game.command(f"data get entity {uuid} CustomNameVisible").rstrip().endswith("1b")   # the slime: no name
        game.command(f"scoreboard players set {uuid} aoe_hp 550")       # repaired (game/repair.py)
        game.command(f"aoe label {uuid}")
        assert label(game) is None
        game.command(f"tag {uuid} add aoe2mc.selected")
        game.command(f"aoe label {uuid}")
        assert label(game) == (5, 0, 208.5)                            # selected: it shows
        game.command(f"tag {uuid} remove aoe2mc.selected")
        game.command(f"scoreboard players set {uuid} aoe_hp 1")
        game.command(f'summon zombie 6.5 {y} 10.5 {{NoAI:1b,IsBaby:0b,Tags:["a"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command(combat.stats_command("@e[tag=a,limit=1]", "CHAMPION"))
        game.command(f"aoe attack @e[tag=a] {uuid}")
        end = time.time() + 30
        while time.time() < end and "passed" in game.command(f"execute if entity {uuid}"):
            time.sleep(0.2)
        assert "passed" not in game.command(f"execute if entity {uuid}")   # the house fell
        assert label(game) is None                                     # and its name line went with it
