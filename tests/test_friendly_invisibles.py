"""aoe2mc.team_lines and game/gather.py: the teams pN do not show invisible team mates (#1538). The target of a
building is an invisible slime in the team of its player (combat.building): with the vanilla default
seeFriendlyInvisibles true, the player saw it as a translucent cube around each own building."""
import json
import os
import shutil
import time

import pytest
from test_loom import setup

import aoe2mc


def test_each_team_of_a_converted_world_hides_its_invisible_members():
    objects = [{"kind": "U", "player": n} for n in (1, 2, 0)]
    load, _ = aoe2mc.team_lines(objects, {})
    for n in (1, 2):
        assert f"team modify p{n} seeFriendlyInvisibles false" in load
        assert load.index(f"team modify p{n} seeFriendlyInvisibles false") > load.index(f'team add p{n} "Player {n}"')
    assert not any("p0" in c for c in load)


def test_setup_hides_them_also_in_a_world_of_an_earlier_version():
    server, g = setup()
    assert server.log.index("team modify p1 seeFriendlyInvisibles false") < server.log.index("team join p1 @a")


@pytest.mark.mc
def test_a_real_player_sees_no_cube_at_an_own_building(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import mc_shot
    from PIL import Image, ImageChops

    from game import combat, gather, run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    y = 200                                                            # a floor in the air, inside the world border
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        for c in ("forceload add 0 0 40 40", f"fill 0 {y - 1} 0 39 {y - 1} 39 stone_bricks", "time set noon",
                  "gamerule advance_time false", "weather clear", "team add p1"):
            game.command(c)
        gather.Gather(game, data).setup()
        assert "aoe2mc" in game.command("team list p1")
        game.command("gamemode adventure aoe2mc")
        game.command(f"tp aoe2mc 20.5 {y} 38.5 180 -15")                 # south of the building, the sky behind its top
        time.sleep(8)                                                  # the toasts of the join go away
        uuid = combat.target_uuid([12, 12, 28, 28])
        shots = {}

        def shot(name):
            time.sleep(3)
            client.shot(str(tmp_path / f"{name}.png"))
            im = Image.open(tmp_path / f"{name}.png").convert("L")
            im = im.crop((im.width // 5, 0, im.width * 9 // 20, im.height // 2))   # no toast, sidebar, map
            shots[name] = im.resize((im.width // 16, im.height // 16), Image.BOX)   # the sky dither moves in each frame
        shot("empty")
        for c in combat.building(uuid, "BARRACKS", 1, (12, y, 12, 27, y + 12, 27)):
            game.command(c)
        shot("hidden")
        game.command("team modify p1 seeFriendlyInvisibles true")       # the vanilla default: the cube shows
        shot("cube")

    def changed(a, b):                                                 # the number of 16 x 16 cells that changed
        return sum(ImageChops.difference(shots[a], shots[b]).point(lambda v: 255 * (v > 12)).histogram()[255:])
    total = shots["empty"].size[0] * shots["empty"].size[1]
    assert changed("empty", "cube") > total // 4, "the translucent slime did not show with seeFriendlyInvisibles true"
    assert changed("empty", "hidden") == 0, "the player sees the invisible slime of the own building"
