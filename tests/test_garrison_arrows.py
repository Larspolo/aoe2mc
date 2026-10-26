"""Each garrisoned villager or foot archer adds one arrow to its town center, tower or castle (#1113):
garrison.arrows and `aoe arrows` of the plugin."""
import shutil
import time

import pytest
from test_garrison_game import TC, arrive, setup

from game import combat, garrison, run
from test_damage import health


def test_town_center_with_3_villagers_shoots_4_arrows():
    assert garrison.arrows([]) == 1
    assert garrison.arrows(["VILLAGER_MALE", "VILLAGER_FEMALE", "VILLAGER"]) == 4
    assert garrison.arrows(["ARCHER", "HAND_CANNONEER"]) == 3                # foot archers
    assert garrison.arrows(["CAVALRY_ARCHER", "MILITIA", "KNIGHT"]) == 1      # no foot archer


def test_garrison_and_ungarrison_send_the_arrows():
    server, g = setup()
    uuid = combat.target_uuid([TC[0], TC[2], TC[1], TC[3]])
    g.choose({"v0", "v1", "v2"}, "v0")
    garrison.order(g, "Steve", (3, 3))
    arrive(server, g, TC)
    assert [c for c in server.log if c.startswith("aoe arrows")] == [f"aoe arrows {uuid} {n}" for n in (2, 3, 4)]
    garrison.out(g, TC)
    assert server.log.count(f"aoe arrows {uuid} 1") == 1


@pytest.mark.mc
def test_town_center_with_3_villagers_does_4_times_the_damage(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                    # a floor in the air, inside the world border
    box = (20, y, 20, 35, y + 40, 35)          # a town center of 4 x 4 tiles
    uuid = combat.target_uuid([20, 20, 36, 36])
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")      # zombies burn in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon zombie 48.5 {y} 28.5 {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')   # 12 blocks from the edge
        game.command("team join p2 @e[tag=e]")
        game.command("aoe stats @e[tag=e,limit=1] 1000 4 0 1 0 infantry - 20")    # pierce armor 1, many hit points
        for c in combat.building(uuid, "TOWN_CENTER", 1, box):
            game.command(c)

        def rate():
            """Damage per second on the enemy: from its first hit after now, for 6 s."""
            h = health(game, "e")
            for _ in range(40):
                if health(game, "e") < h:
                    break
                time.sleep(0.1)
            h0, t0 = health(game, "e"), time.time()
            time.sleep(6)
            return (h0 - health(game, "e")) / (time.time() - t0)

        alone = rate()
        assert game.command(f"aoe arrows {uuid} {garrison.arrows(['VILLAGER'] * 3)}").strip() == "Arrows: 4"
        full = rate()
        assert alone > 0 and 3.2 <= full / alone <= 4.8, (alone, full)        # 4 per arrow: attack 5 - pierce 1
