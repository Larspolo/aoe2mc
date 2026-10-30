"""The Centurion makes the own Militia-line units near it move and attack faster (#4470, AoE2 wiki "Centurion": the
ability Imperium; no stack, not for allies): the key "aura", combat.aura_command and `aoe aura` of the plugin. Test
data, and units on a server."""
import shutil
import time

import pytest

from game import combat, run

AURA = {"TEST_LEADER": {"radius": 3, "speed": 0.1, "attack_speed": 0.2, "units": ["MILITIA", "CHAMPION"]}}


def test_the_aura_command_gives_the_blocks_the_factors_and_the_tag(monkeypatch):
    monkeypatch.setattr(combat, "AURA", AURA)
    assert combat.aura_command("u-1", "TEST_LEADER", 4) == "aoe aura u-1 12 0.1 0.2 aoe2mc.aura.test_leader"
    assert combat.aura_command("u-1", "KNIGHT", 4) is None


def test_the_units_of_the_aura_get_its_tag(monkeypatch):
    monkeypatch.setattr(combat, "AURA", AURA)
    assert combat.aura_tags("u-1", "CHAMPION") == ["tag u-1 add aoe2mc.aura.test_leader"]
    assert combat.aura_tags("u-1", "KNIGHT") == []


def modifier(game, tag):
    """The aura modifier of the movement speed of the unit with tag, or None."""
    out = game.command(f"attribute @e[tag={tag},limit=1] minecraft:movement_speed modifier value get aoe2mc:aura")
    return None if "No modifier" in out or "no modifier" in out.lower() else out


@pytest.mark.mc
def test_own_units_with_the_tag_near_the_aura_get_the_speed(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, tag = 200, "aoe2mc.aura.test"
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
        assert game.command(f"aoe aura @e[tag=c] 12 0.1 0.2 {tag}").strip() == "Aura: 2 units"   # two Centurions
        time.sleep(2.5)
        assert modifier(game, "m") is not None and "0.1" in modifier(game, "m")
        assert modifier(game, "e") is None and modifier(game, "o") is None     # an enemy; no tag
        game.command("tp @e[tag=m] 28.5 200 28.5")
        time.sleep(2.5)
        assert modifier(game, "m") is None
