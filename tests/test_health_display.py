"""The name line over units and buildings of the game program (#661, owner decision #658): the name and 5 hearts,
visible only when the unit is hurt or selected. AoePlugin.java draws it; game/combat.py and game/gather.py ask for it."""
import shutil
import time

import pytest
from test_bossbar import setup

from game import combat


def test_label_commands():
    assert combat.label_command("u") == "aoe label u"
    assert combat.label_command("u", "SIEGE_WORKSHOP") == "aoe label u Siege Workshop"


def test_a_selection_change_updates_the_name_lines():
    server, g = setup()
    del server.log[:]
    g.select("v")
    assert [c for c in server.log if c.startswith("aoe label")] == ["aoe label v"]
    del server.log[:]
    g.select("m")                                                      # v is not selected now
    assert [c for c in server.log if c.startswith("aoe label")] == ["aoe label m", "aoe label v"]
    del server.log[:]
    g.select("a")                                                      # a military unit adds to the military selection
    assert [c for c in server.log if c.startswith("aoe label")] == ["aoe label a"]


def hearts(game, uuid):
    """(red hearts, gray hearts, visible) of the name line of entity uuid."""
    def part(i):                                                    # the full output cuts deep compounds ("...")
        out = game.command(f"data get entity {uuid} CustomName.extra[{i}].text")
        assert "has the following entity data" in out, out
        return out.rsplit(":", 1)[1].count("❤")
    visible = game.command(f"data get entity {uuid} CustomNameVisible")
    return part(2), part(3), visible.rstrip().endswith("1b")


@pytest.mark.mc
def test_the_name_line_shows_hearts_when_hurt_or_selected(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json

    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import gather, run
    scn = scenarios.new_scenario(16)
    for x in (6.5, 9.5):
        scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=x, y=8.5)
    src = str(tmp_path / "hp.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data).setup()
        a, b = sorted(g.soldiers)
        assert hearts(game, a) == (5, 0, False)                         # full hit points, not selected: hidden
        assert "Militia" in game.command(f"data get entity {a} CustomName")
        g.select(a)
        assert hearts(game, a) == (5, 0, True)
        game.command(f"damage {b} 15")                                  # 25 of 40 hit points: 4 hearts
        time.sleep(0.5)
        assert hearts(game, b) == (4, 1, True)
        game.command(f"tag {a} remove {gather.SELECT}")                 # not selected: the line goes
        assert game.command(combat.label_command(a)).strip() == "Label: 1 units"
        assert hearts(game, a) == (5, 0, False) and hearts(game, b) == (4, 1, True)


@pytest.mark.mc
def test_a_hit_building_shows_its_name_line(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, box = 200, (8, 200, 8, 13, 240, 13)                             # a house in the air, as test_building_damage
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command(f"fill 0 {y - 1} 0 21 {y - 1} 21 stone_bricks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        uuid = combat.target_uuid([8, 8, 14, 14])
        for c in combat.building(uuid, "HOUSE", 2, box):
            game.command(c)
        assert game.command(combat.label_command(uuid, "HOUSE")).strip() == "Label: 1 units"
        assert hearts(game, uuid) == (5, 0, False) and "House" in game.command(f"data get entity {uuid} CustomName")
        game.command(f'summon zombie 4.5 {y} 10.5 {{NoAI:1b,IsBaby:0b,Tags:["a"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command(combat.stats_command("@e[tag=a,limit=1]", "CHAMPION"))
        game.command(f"aoe attack @e[tag=a] {uuid}")
        end = time.time() + 30
        label = "execute if entity @e[type=text_display,tag=aoe2mc.label]"
        while time.time() < end and "passed" not in game.command(label):
            time.sleep(0.2)
        assert "passed" in game.command(label)                         # the name line over the roof (#1811)
        assert hearts(game, uuid) == (5, 0, False)                      # 537 of 550: still 5 hearts; the slime hides its name
