"""The Monaspa gets +1 attack for every 7 own Monaspas or Knight-line units within 15 tiles, up to +4 (#4469, AoE2
wiki "Monaspa"): the key "pack", game/abilities/pack.py and `aoe pack` of the plugin. Test data, and hits on a server."""
import shutil

import pytest
from abilities import pack
from test_veteran import first_loss, uuid

from game import combat, run


def test_the_pack_command_gives_the_per_the_blocks_the_max_and_the_type_tags(monkeypatch):
    monkeypatch.setattr(pack, "UNITS", {"KNIGHT": {"per": 7, "radius": 15, "max": 4, "with": ["KNIGHT", "CAVALIER"]}})
    ids = combat.units.type_ids()
    assert pack.command("u-1", "KNIGHT", 4) == f"aoe pack u-1 7 60 4 aoe2mc.t{ids['KNIGHT']},aoe2mc.t{ids['CAVALIER']}"
    assert pack.command("u-1", "ARCHER", 4) is None


@pytest.mark.mc
def test_7_own_units_give_1_more_damage_14_give_2_and_enemies_do_not_count(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    with run.Game(world) as game:
        game.command("forceload add 0 0 16 16")
        game.command(f"fill 0 {y - 1} 0 15 {y - 1} 15 stone_bricks")
        game.command("time set midnight")                 # a zombie burns in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon zombie 3.5 {y} 11.5 {{NoAI:1b,IsBaby:0b,UUID:[I;1,2,3,4],Tags:["t"]}}')
        game.command(f"aoe stats {uuid(1)} 1000 0 0 0 0 cavalry -")
        game.command("team join p2 @e[tag=t]")
        game.command(f'summon zombie 3.5 {y} 8.5 {{IsBaby:0b,Tags:["m"]}}')
        game.command("team join p1 @e[tag=m]")
        game.command(combat.stats_command("@e[tag=m,limit=1]", "MILITIA"))
        assert game.command("aoe pack @e[tag=m,limit=1] 7 20 4 aoe2mc.k").strip() == "Pack: 1 units"

        def mates(n, team, tag):                          # n units with the type tag that stand still
            for k in range(n):
                game.command(f'summon zombie {9.5 + k % 5} {y} {2.5 + k // 5} {{NoAI:1b,IsBaby:0b,'
                             f'Tags:["aoe2mc.k","{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")

        def hit():
            import time
            time.sleep(2.5)                               # one AoE2 reload: the next hit is a new one
            return first_loss(game, "m", 1)

        alone = hit()
        mates(7, "p2", "e")                               # enemies with the tag do not count
        assert hit() == pytest.approx(alone)
        mates(7, "p1", "a")
        assert hit() == pytest.approx(alone + 1)
        mates(7, "p1", "b")
        assert hit() == pytest.approx(alone + 2)
