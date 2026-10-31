"""game/gather.py: an attack order on a building marks the building (#991): its target glows SIEGE_GLOW seconds, and
the action bar shows its name and hit points (the score of the plugin)."""
import json
import shutil

import pytest
import test_gather_attack
from test_gather_attack import click

from game import combat, gather


def test_siege_mark_glows_and_shows_name_and_hit_points():
    glow, bar = gather.siege_mark("fort", "STABLE", 1500, "Steve")
    assert glow == f"effect give fort minecraft:glowing {gather.SIEGE_GLOW} 0 true" and 2 <= gather.SIEGE_GLOW <= 3
    assert bar.startswith("title Steve actionbar ")
    text = json.loads(bar.split(" ", 3)[3])
    assert text["translate"] == "aoe2mc.gather.attack_siege"
    assert text["with"] == ["Stable", {"score": {"name": "fort", "objective": "aoe_hp"}}, "1500"]


def test_an_attack_order_on_a_building_marks_it():
    server, g = test_gather_attack.setup()
    click(server, g, (5.5, 13.5), (5.5, 10.5))                         # select the militia
    g.forts["fort"], g.fort_names["fort"] = (14, 64, 2, 17, 70, 5), "BARRACKS"
    log = click(server, g, (15.5, 9.5), (15.5, 4.0))
    glow, bar = gather.siege_mark("fort", "BARRACKS", combat.stats("BARRACKS").hp, "Steve")
    assert glow in log and bar in log
    assert log.index("aoe attack @e[tag=aoe2mc.selected] fort") < log.index(glow)


@pytest.mark.mc
def test_the_siege_mark_commands_work_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.forceload()
        from game import combat
        uuid = combat.target_uuid([8, 8, 11, 11])
        for c in combat.building(uuid, "STABLE", 2, (8, 64, 8, 10, 70, 10)):
            game.command(c)
        assert game.command(f"scoreboard players get {uuid} aoe_hp").endswith("1500 [Hit points]"), uuid
        answers = [game.command(c) for c in gather.siege_mark(uuid, "STABLE", 1500, "@a")]
        assert answers[0].startswith("Applied effect"), answers
        assert all("<--[HERE]" not in a and "Unknown" not in a for a in answers), answers
