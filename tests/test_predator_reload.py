"""A predator of Gaia hits once per AoE2 reload, as at Normal speed (#3624): a wolf and a hoglin bear."""
import shutil
import time

import pytest
from test_damage import health
from test_stances_kinds import summon

from game import combat, run
from game.gather import NORMAL


def kill_time(game, kind, tag):
    """Seconds from the first hit on a villager with NoAI next to predator `kind` to its death, and the hits."""
    v, p = f"v{tag}", f"p{tag}"
    assert "Summoned" in summon(game, "VILLAGER_MALE", (4 + 12 * tag, 151, 4), v)
    game.command(f"data merge entity @e[tag={v}r,limit=1] {{NoAI: 1b}}")
    game.command(f"team join p1 @e[tag={v}]")
    assert game.command(combat.stats_command(f"@e[tag={v}r,limit=1]", "VILLAGER_MALE")).strip() == "Stats: 1 units"
    full = health(game, f"{v}r")
    assert "Summoned" in summon(game, kind, (4 + 12 * tag, 151, 6), p)
    combat.setup(game, {"objects": [{"kind": "unit", "name": kind, "player": 0, "uuid": f"@e[tag={p}r,limit=1]"}],
                        "tile_size": 4})
    first, end = None, time.time() + 60
    while time.time() < end:
        hp = health(game, f"{v}r")
        if hp is None:
            game.command(f"kill @e[tag={p}]")                    # else it attacks the next villager
            return time.time() - first, full
        if first is None and hp < full:
            first = time.time()
        time.sleep(0.1)
    pytest.fail(f"{kind} did not kill the villager: {health(game, f'{v}r')} hp")


@pytest.mark.mc
def test_a_wolf_and_a_bear_hit_once_per_reload(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    import mc_shot
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    with run.Game(shutil.copytree(tiny_world[0], tmp_path / "W")) as game, \
            mc_shot.Client(game.game_port, game.version) as client:
        game.command("forceload add 0 0 40 40")
        assert wait_fill(game)
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("gamemode spectator aoe2mc")
        game.command("tp aoe2mc 10 155 10")
        for tag, kind in enumerate(("WOLF", "BROWN_BEAR")):
            secs, full = kill_time(game, kind, tag)
            s = combat.stats(kind)
            hits = -(-full // s.attack)
            want = (hits - 1) * s.reload / NORMAL                  # the first hit starts the clock
            assert 0.8 * want <= secs <= 1.2 * want, (kind, secs, want)


def wait_fill(game):
    end = time.time() + 20
    while time.time() < end:
        if "filled" in game.command("fill 0 150 0 40 150 40 stone"):     # "No blocks were filled": done
            return True
        time.sleep(0.5)
    return False
