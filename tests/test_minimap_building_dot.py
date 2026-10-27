"""The map item of the live replay draws no unit dot for the target slime of a building (#1800): the slime is in the
team of its player (combat.building), and its dot showed each enemy building through the fog of a view."""
import shutil
import time

import pytest

from game import combat


@pytest.mark.mc
def test_a_building_slime_has_no_dot_and_a_unit_has_one(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("item replace entity aoe2mc weapon.mainhand with minecraft:filled_map[minecraft:map_id=0]")
        game.command("team add p1")
        game.command("team modify p1 color red")
        assert "Minimap: on" in game.command("aoe minimap on")
        time.sleep(3)
        before = game.command("aoe minimap tile 22 22").split()[3], game.command("aoe minimap tile 6 2").split()[3]
        uuid = combat.target_uuid([20, 20, 24, 24])
        for c in combat.building(uuid, "HOUSE", 1, (20, 80, 20, 23, 83, 23)):
            assert "Bad" not in game.command(c)
        game.command('summon zombie 6 80 2 {NoAI:1b,NoGravity:1b,Tags:["u"]}')
        game.command("team join p1 @e[tag=u]")
        time.sleep(3)
        red = str(28 * 4 + 2)                                           # the map color of the red team
        assert game.command("aoe minimap tile 6 2").split()[3] == red != before[1]      # the unit has its dot
        assert game.command("aoe minimap tile 22 22").split()[3] == before[0] != red    # the building has none
