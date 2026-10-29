"""A hit of a Gaia predator gives the unit alert of the player of the target, once per place (#3398)."""
import os
import shutil

import pytest
from test_damage import health
from test_predators import wait
from test_stances_kinds import summon

from game import combat, run


@pytest.mark.mc
def test_a_wolf_hit_gives_one_unit_alert_for_the_player_of_the_villager(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    with run.Game(shutil.copytree(tiny_world[0], tmp_path / "W")) as game:
        game.command("forceload add 0 0 40 40")
        assert wait(lambda: "filled" in game.command("fill 0 150 0 40 150 40 stone"), 20)
        game.command("team add p1")
        assert "Summoned" in summon(game, "VILLAGER_MALE", (4, 151, 4), "vil")
        game.command("team join p1 @e[tag=vil]")
        game.command("data merge entity @e[tag=vilr,limit=1] {NoAI:1b}")              # it stays at one place
        assert game.command(combat.stats_command("@e[tag=vilr,limit=1]", "VILLAGER_MALE")).strip() == "Stats: 1 units"
        game.command("aoe stats @e[tag=vilr,limit=1] 1000 4 0 1 0 infantry - 20")           # many hit points: many hits
        assert "Summoned" in summon(game, "WOLF", (7, 151, 4), "w")
        combat.setup(game, {"objects": [{"kind": "unit", "name": "WOLF", "player": 0, "uuid": "@e[tag=wr,limit=1]"}],
                            "tile_size": 4})
        assert wait(lambda: (health(game, "vilr") or 1000) <= 1000 - 3, 60), health(game, "vilr")  # 2 hits of 2
        with open(os.path.join(game.folder, "logs", "latest.log")) as f:
            alerts = [line for line in f if "Alert " in line]
    assert len(alerts) == 1, alerts                                    # one place, less than 20 s
    assert "Alert p1: Your units are under attack at 4 4" in alerts[0]
