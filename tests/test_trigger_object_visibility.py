"""Triggers hide units and show them again with "Change Object Visibility" (#2862): the effect invisibility of the
units and their mounts (the entity tag Invisible is only for armor stands), and their name tags."""
import contextlib
import io
import shutil

import numpy as np
import pytest

import aoe2mc
from tools import scenarios


def effect(visibility, area=(1, 2, 2, 3), player=2, selected=()):
    return dict(type=aoe2mc.CHANGE_OBJECT_VISIBILITY, message="", player=player, time=0, object=None, tile=[-1, -1],
                area=list(area), target=1, visibility=visibility, selected=list(selected))


def lines(effects, T=4):
    trig = dict(id=8, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], T, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/8.mcfunction", "").splitlines()


def test_invisible_hides_the_units_in_the_area_their_mounts_and_their_name_tags():
    sel = aoe2mc.area_selector(effect(2), 4)
    assert sel.startswith("@e[tag=aoe2mc.p2,") and sel.endswith("]")
    assert lines([effect(2)]) == [
        f"execute as {sel} on vehicle run effect give @s minecraft:invisibility infinite 0 true",
        f"execute as {sel} run effect give @s minecraft:invisibility infinite 0 true",
        f"tag {sel[:-1]},nbt={{CustomNameVisible:1b}}] add {aoe2mc.NAME_HIDDEN}",
        f"execute as {sel} run data merge entity @s {{CustomNameVisible:0b}}"]


def test_explored_hides_them_too():
    assert lines([effect(1)]) == lines([effect(2)])


def test_visible_shows_them_and_only_the_name_tags_that_the_trigger_hid():
    sel = aoe2mc.area_selector(effect(0), 4)
    hid = f"{sel[:-1]},tag={aoe2mc.NAME_HIDDEN}]"
    assert lines([effect(0)]) == [
        f"execute as {sel} on vehicle run effect clear @s minecraft:invisibility",
        f"execute as {sel} run effect clear @s minecraft:invisibility",
        f"execute as {hid} run data merge entity @s {{CustomNameVisible:1b}}",
        f"tag {hid} remove {aoe2mc.NAME_HIDDEN}"]


def test_selected_objects_are_found_by_their_reference_tag():
    out = lines([effect(2, area=(-1, -1, -1, -1), selected=[7])])
    assert out[1] == "execute as @e[tag=aoe2mc.p2,tag=aoe2mc.r7] run effect give @s minecraft:invisibility infinite 0 true"
    assert len(out) == 4 and all("aoe2mc.r7" in x for x in out)


def test_no_area_and_no_selection_or_an_unknown_state_gives_no_line():
    assert lines([effect(2, area=(-1, -1, -1, -1))]) == []
    assert lines([effect(3)]) == []


def test_read_scenario_keeps_the_state_the_target_and_the_selected_objects(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Hide")
    t.new_condition.timer(timer=1)
    t.new_effect.change_object_visibility(source_player=2, target_player=1, visibility_state=2,
                                          selected_object_ids=[7], area_x1=1, area_y1=2, area_x2=2, area_y2=3)
    src = scenarios.save(scn, str(tmp_path / "a.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = trigger["effects"]
    assert e["type"] == aoe2mc.CHANGE_OBJECT_VISIBILITY and e["visibility"] == 2 and e["target"] == 1
    assert e["selected"] == [7] and e["player"] == 2 and e["area"] == [1, 2, 2, 3]


@pytest.mark.mc
def test_the_commands_hide_a_rider_its_horse_and_its_name_on_a_server(tiny_world, tmp_path):
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.command("forceload add 0 0 15 15")
        game.command('summon horse 6 200 6 {NoAI:1b,NoGravity:1b,Tags:["aoe2mc.p2","aoe2mc.mount","h"],'
                     'Passengers:[{id:"minecraft:zombie",NoAI:1b,Tags:["aoe2mc.p2","u"],'
                     'CustomName:{text:"Knight"},CustomNameVisible:1b}]}')
        say = [game.command(x) for x in lines([effect(2, area=(0, 0, 3, 3))])]
        assert not any("Unknown" in s or "Incorrect" in s or "Expected" in s for s in say), say
        for tag in ("u", "h"):
            assert "minecraft:invisibility" in game.command(f"data get entity @e[tag={tag},limit=1] active_effects")
        assert "aoe2mc.name_hidden" in game.command("data get entity @e[tag=u,limit=1] Tags")
        assert not game.command("data get entity @e[tag=u,limit=1] CustomNameVisible").strip().endswith("1b")
        say = [game.command(x) for x in lines([effect(0, area=(0, 0, 3, 3))])]
        for tag in ("u", "h"):
            assert "invisibility" not in game.command(f"data get entity @e[tag={tag},limit=1] active_effects")
        assert game.command("data get entity @e[tag=u,limit=1] CustomNameVisible").strip().endswith("1b")
        assert "name_hidden" not in game.command("data get entity @e[tag=u,limit=1] Tags")
