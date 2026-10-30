"""game/gather.py: the human player gets the side of the own units, so the plugin sends the attack alerts of the team
(#1231) to the player (#1241). The scoreboard team, not the tag aoe2mc.pN: cheats.destroy kills and conquest.alive
counts the entities with that tag."""
import json
import os
import shutil
import time

import pytest
from test_loom import setup

from game import gather


def test_setup_puts_the_online_players_in_the_team_of_the_player():
    server, g = setup()
    assert "team join p1 @a" in server.log
    assert not any(c.startswith("tag ") and "aoe2mc.p" in c for c in server.log)


def test_a_player_who_joins_later_gets_the_team_once():
    server, g = setup()
    g.point()
    g.point()
    assert server.log.count("team join p1 Steve") == 1


def test_the_team_is_the_one_of_the_player_of_the_game():
    server, g = setup()
    g2 = gather.Gather(server, g.data, 2).setup()
    assert "team join p2 @a" in server.log and g2.player == 2


@pytest.mark.mc
def test_a_real_player_sees_the_alert_of_the_own_units_only(tiny_world, tmp_path):
    from test_damage import health
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import mc_shot

    from game import combat, run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    y = 200                                                            # a floor in the air, inside the world border
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version, chat=True) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")                              # zombies burn in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        g = gather.Gather(game, data).setup()
        assert "aoe2mc" in game.command("team list p1")
        game.command(f"tp aoe2mc 75 {y} 75")                       # out of the range of the enemy castle
        for tag, team, z in (("e", "p1", 28.5), ("f", "p2", 68.5)):   # an own unit, and an enemy unit
            game.command(f'summon zombie 48.5 {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry - 20")
        for player, z0 in ((2, 20), (1, 60)):                          # an enemy castle and an own castle
            for c in combat.building(combat.target_uuid([20, z0, 36, z0 + 16]), "CASTLE", player,
                                     (20, y, z0, 35, y + 40, z0 + 15)):
                game.command(c)
        end = time.time() + 30
        while health(game, "e") > 1000 - 50 or health(game, "f") > 1000 - 50:
            assert time.time() < end, "the castles did not shoot"
            time.sleep(0.2)
        time.sleep(2)
        client.shot(str(tmp_path / "alert.png"))
        chat = [line for line in client.text().splitlines() if "[CHAT]" in line]
        with open(os.path.join(game.folder, "logs", "latest.log")) as f:
            alerts = [line for line in f if "Alert " in line]
    assert any("Alert p2:" in a for a in alerts), alerts               # the plugin saw the hit on the enemy unit
    assert any("Your units are under attack at 48 28" in c for c in chat), chat
    assert not any("at 48 68" in c for c in chat), chat
    assert g.player == 1
