"""A melee unit hits once per AoE2 reload time (#848): game/combat.py stats_command and the plugin on Paper."""
import shutil
import time

import pytest
from test_building_damage import hp
from test_damage import health

from game import combat, run


def test_the_stats_command_ends_with_the_reload_in_ticks():
    assert combat.stats_command("c", "X", combat.Stats(1, 1, 0, 0, 0, 2.0)).split()[-1] == "24"   # 2.0 s / 1.7 = 1.18 s
    assert combat.stats_command("p", "X", combat.Stats(1, 1, 0, 0, 0, 3.0)).split()[-1] == "35"   # 3.0 s / 1.7 = 1.76 s
    assert combat.stats_command("x", "X", combat.Stats(1, 1, 0, 0, 0, 0.0)).split()[-1] == "20"   # no reload: vanilla


def times(game, read, n, end=60):
    """The wall times of the first n changes of read() (a value of hit points), or fewer at the end."""
    seen, at, stop = [read()], [], time.time() + end
    while len(at) < n and time.time() < stop:
        h = read()
        if h != seen[-1]:
            seen.append(h)
            at.append(time.time())
        time.sleep(0.02)
    return seen, at


@pytest.mark.mc
def test_melee_units_hit_once_per_reload(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 40} {z0 + 40}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 36} {y - 1} {z0 + 36} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        for tag, dz, name in (("c", 2, "CHAMPION"), ("ct", 2, None), ("p", 20, "PIKEMAN"), ("pt", 20, None)):
            x = x0 + (2 if tag in ("c", "p") else 4) + 0.5
            game.command(f'summon zombie {x} {y} {z0 + dz + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {'p1' if name else 'p2'} @e[tag={tag}]")
            cmd = combat.stats_command(f"@e[tag={tag},limit=1]", name) if name else \
                f"aoe stats @e[tag={tag},limit=1] 1000 0 0 0 0 infantry -"     # a target that does not hit back
            assert game.command(cmd).strip() == "Stats: 1 units"
        for a in ("c", "p"):
            assert game.command(f"aoe attack @e[tag={a}] @e[tag={a}t,limit=1]").strip() == "Attack: 1 units"
        target = combat.Stats(1000, 0, 0, 0, 0, 0.0, classes=("infantry",))
        for a, name in (("c", "CHAMPION"), ("p", "PIKEMAN")):
            step = int(combat.stats_command(a, name).split()[-1]) / 20
            per = combat.damage(name, "X", t=target)
            seen, at = times(game, lambda: health(game, a + "t"), 6)
            assert len(at) == 6 and all(x - y == per for x, y in zip(seen, seen[1:])), seen
            gaps = [b - a for a, b in zip(at, at[1:])]
            assert all(abs(g - step) < 0.15 for g in gaps), gaps


@pytest.mark.mc
def test_three_champions_destroy_a_stable_at_the_aoe2_rate(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, box = 200, (8, 200, 8, 13, 240, 13)                             # a building in the air, inside the world border
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command(f"fill 0 {y - 1} 0 21 {y - 1} 21 stone_bricks")
        game.command(f"fill 8 {y} 8 13 {y + 3} 13 oak_planks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        uuid = combat.target_uuid([8, 8, 14, 14])
        for c in combat.building(uuid, "STABLE", 2, box):
            game.command(c)
        for tag, x, z in (("a", 4.5, 10.5), ("b", 17.5, 10.5), ("c", 10.5, 4.5)):
            game.command(f'summon zombie {x} {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p1 @e[tag={tag}]")
            game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "CHAMPION"))
            assert game.command(f"aoe attack @e[tag={tag}] {uuid}").strip() == "Attack: 1 units"
        seen, at = times(game, lambda: hp(game, uuid), 200, end=80)
        assert seen[-1] is None, seen                                  # destroyed
        assert abs(at[-1] - at[0] - 116 / 3 * 24 / 20) < 4, (at[-1] - at[0], seen)   # 116 hits of 13, 1.2 s each
