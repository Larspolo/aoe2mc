"""The predators of Gaia wake up at the start of a game and attack the units of the players (#3397)."""
import shutil
import time

import pytest
from test_damage import health
from test_stances_kinds import summon

from game import combat, run


class Game:
    def __init__(self):
        self.sent = []

    def command(self, cmd):
        self.sent.append(cmd)
        return "Stats: 1 units"


def test_setup_wakes_a_wolf_of_gaia_and_not_a_deer():
    data = {"objects": [{"kind": "unit", "name": "WOLF", "player": 0, "uuid": "w"},
                        {"kind": "unit", "name": "DEER", "player": 0, "uuid": "d"}], "tile_size": 4}
    game = Game()
    combat.setup(game, data)
    assert [c.split()[:3] for c in game.sent if c.split()[1] in ("stats", "sight")] == \
        [["aoe", "stats", "w"], ["aoe", "sight", "w"]]
    assert combat.sight_command("w", "WOLF", 4) and combat.sight_command("d", "DEER", 4) is None


def wait(cond, secs):
    end = time.time() + secs
    while not cond() and time.time() < end:
        time.sleep(0.5)
    return cond()


@pytest.mark.mc
def test_a_wolf_kills_a_lone_villager_and_spares_wolves_and_people(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    import mc_shot
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    with run.Game(shutil.copytree(tiny_world[0], tmp_path / "W")) as game, \
            mc_shot.Client(game.game_port, game.version) as client:
        game.command("forceload add 0 0 40 40")
        assert wait(lambda: "filled" in game.command("fill 0 150 0 40 150 40 stone"), 20)   # "No blocks were filled": done
        assert "Summoned" in summon(game, "VILLAGER_MALE", (4, 151, 4), "vil")
        game.command("team join p1 @e[tag=vil]")
        assert game.command(combat.stats_command("@e[tag=vilr,limit=1]", "VILLAGER_MALE")).strip() == "Stats: 1 units"
        for tag, pos in (("w1", (7, 151, 4)), ("w2", (30, 151, 30)), ("w3", (32, 151, 30))):
            assert "Summoned" in summon(game, "WOLF", pos, tag)
        data = {"objects": [{"kind": "unit", "name": "WOLF", "player": 0, "uuid": f"@e[tag={t}r,limit=1]"}
                            for t in ("w1", "w2", "w3")], "tile_size": 4}
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("gamemode survival aoe2mc")
        game.command("tp aoe2mc 31 151 32")                    # next to the two other wolves
        combat.setup(game, data)
        assert wait(lambda: health(game, "vilr") is None, 60), health(game, "vilr")   # the villager died
        time.sleep(10)
        assert health(game, "w2r") == health(game, "w3r") == 20.0             # the wolves do not fight
        out = game.command("data get entity aoe2mc Health")
        assert "20.0f" in out, out                                             # the person takes no damage
