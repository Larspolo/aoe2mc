"""Live replay: a unit that the fog hides from a player gives no death mark that the player sees (#3084, Deaths.java).
Replay.fog hides the unit with `aoe hide`; the mark of its death must stay hidden too."""
import re
import shutil
import time

import pytest
import replay

from game import run


def mark_uuid(game):
    """The UUID of the one death mark, from its NBT int array."""
    ints = re.search(r"\[I;\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\]",
                     game.command("data get entity @e[type=text_display,tag=aoe2mc.deathmark,limit=1] UUID"))
    h = "".join(f"{int(i) & 0xffffffff:08x}" for i in ints.groups())
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


@pytest.mark.mc
def test_a_hidden_unit_leaves_no_mark_for_the_player(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.forceload()
        with mc_shot.Client(game.game_port, game.version) as client:
            client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
            time.sleep(2)
            assert "Death marks: on" in game.command("aoe deathmarks on")
            for i, hidden in ((3084, True), (3085, False)):
                uuid = f"00000000-0000-0000-0000-{i:012x}"
                game.command(f'summon minecraft:pillager 8 80 8 {{UUID:[I;0,0,0,{i}],NoAI:1b,'
                             f'Tags:["{replay.COUNTED}"]}}')
                if hidden:
                    game.command(f"aoe hide @a {uuid}")
                    time.sleep(1)
                    assert game.command(f"aoe sees aoe2mc {uuid}").strip() == "Sees: 0"
                game.command(f"kill {uuid}")
                time.sleep(1)
                mark = mark_uuid(game)
                assert game.command(f"aoe sees aoe2mc {mark}").strip() == f"Sees: {0 if hidden else 1}"
                game.command("kill @e[type=text_display,tag=aoe2mc.deathmark]")
