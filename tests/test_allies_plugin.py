"""Allied players are one side in the plugin (#1315): the arrows of buildings, the hit back and the attack alerts."""
import shutil
import time

import pytest
from test_damage import health

from game import combat, gather, run


def test_allies_command_groups_the_teams_of_aoe2mc_json():
    players = {"1": {"team": 1}, "2": {"team": 2}, "3": {"team": 1}, "4": {}, "10": {"team": 2}}
    assert gather.allies_command(players) == "aoe allies p1,p3 p2,p10"
    assert gather.allies_command({"1": {"team": 1}, "2": {}}) == "aoe allies -"     # one player alone: no alliance
    assert gather.allies_command({}) == "aoe allies -"


@pytest.mark.mc
def test_a_town_center_shoots_the_enemy_and_not_the_ally(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                    # a floor in the air, inside the world border
    box = (20, y, 20, 35, y + 40, 35)          # a town center of 4 x 4 tiles of player 1
    uuid = combat.target_uuid([20, 20, 36, 36])
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")      # zombies burn in the sun
        for t in ("p1", "p2", "p3"):
            game.command(f"team add {t}")
        assert game.command("aoe allies p1,p2").startswith("Allies:")
        # a: a unit of the allied player 2, 4 blocks from the edge; e: an enemy of player 3, 12 blocks from the edge
        for tag, (x, z, team) in {"a": (40.5, 28.5, "p2"), "e": (28.5, 48.5, "p3")}.items():
            game.command(f'summon zombie {x} {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "MILITIA"))
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry - 20")
        for c in combat.building(uuid, "TOWN_CENTER", 1, box, inside=["VILLAGER"]):
            game.command(c)
        t0 = time.time()
        while health(game, "e") == 1000.0 and time.time() - t0 < 5:
            time.sleep(0.1)
        assert health(game, "e") < 1000 and health(game, "a") == 1000.0        # the enemy, not the nearer ally
        game.command("aoe allies -")                                            # no allies: player 2 is an enemy
        t0 = time.time()
        while health(game, "a") == 1000.0 and time.time() - t0 < 5:
            time.sleep(0.1)
        assert health(game, "a") < 1000
