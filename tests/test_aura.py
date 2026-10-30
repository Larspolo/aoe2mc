"""The Centurion makes the own Militia-line units near it move and attack faster (#4470, AoE2 wiki "Centurion": the
ability Imperium; no stack, not for allies): the key "aura", game/abilities/aura.py and `aoe aura` of the plugin. Test
data, and units on a server."""
import shutil
import time

import abilities
import pytest
import units
from abilities import aura

from game import run

AURA = {"TEST_LEADER": {"radius": 3, "speed": 0.1, "attack_speed": 0.2, "units": ["MILITIA", "CHAMPION"]}}


def test_the_aura_command_gives_the_blocks_the_factors_and_the_type_tags(monkeypatch):
    monkeypatch.setattr(aura, "UNITS", AURA)
    ids = units.type_ids()
    tags = f"aoe2mc.t{ids['MILITIA']},aoe2mc.t{ids['CHAMPION']}"
    assert aura.command("u-1", "TEST_LEADER", 4) == f"aoe aura u-1 12 0.1 0.2 {tags}"
    assert aura.command("u-1", "KNIGHT", 4) is None
    assert aura.command("u-1", "TEST_LEADER", 4) in abilities.commands("u-1", "TEST_LEADER", 4)


def modifier(game, tag):
    """The aura modifier of the movement speed of the unit with tag, or None."""
    out = game.command(f"attribute @e[tag={tag},limit=1] minecraft:movement_speed modifier value get aoe2mc:aura")
    return None if "no modifier" in out.lower() else out


@pytest.mark.mc
def test_own_units_with_the_tag_near_the_aura_get_the_speed(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, tag = 200, "aoe2mc.t74"
    with run.Game(world) as game:
        game.command("forceload add 0 0 32 32")
        game.command(f"fill 0 {y - 1} 0 31 {y - 1} 31 stone_bricks")
        game.command("time set midnight")                 # a zombie burns in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        for name, x, team, tags in (("c", 4.5, "p1", '"c"'), ("d", 5.5, "p1", '"c"'), ("m", 6.5, "p1", f'"m","{tag}"'),
                                    ("e", 7.5, "p2", f'"e","{tag}"'), ("o", 8.5, "p1", '"o"')):
            game.command(f"summon zombie {x} {y} 4.5 {{NoAI:1b,IsBaby:0b,Tags:[{tags}]}}")
            game.command(f"team join {team} @e[tag={name}]")
        out = game.command(f"aoe aura @e[tag=c] 12 0.1 0.2 aoe2mc.t1,{tag}")
        assert out.strip() == "Aura: 2 units"            # two Centurions
        time.sleep(2.5)
        assert modifier(game, "m") is not None and "0.1" in modifier(game, "m")   # one modifier: no stack
        assert modifier(game, "e") is None and modifier(game, "o") is None     # an enemy; no tag
        game.command(f"tp @e[tag=m] 28.5 {y} 28.5")
        time.sleep(2.5)
        assert modifier(game, "m") is None
