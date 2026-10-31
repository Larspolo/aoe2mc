"""#5342: an enemy hit on an own unit or building switches the music of the player to a battle track once; the
"calm" seconds with no hit switch it back to a peace track; a hit of another player changes nothing."""
import os
import shutil
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import music  # noqa: E402
from test_scenario_mode import game  # noqa: E402

BATTLE = [{"name": "minecraft:music_disc.pigstep", "use": "battle", "seconds": 600, "calm": 20},
          {"name": "minecraft:music_disc.otherside", "use": "battle", "seconds": 600, "calm": 20}]


def setup(monkeypatch):
    server, g, _ = game({"0": {}, "1": {}, "2": {}})
    now, hit = [100.0], set()
    g.clock = lambda: now[0]
    monkeypatch.setattr(music, "BATTLE", BATTLE)                       # test data: long tracks, 20 s of calm
    monkeypatch.setattr(music, "hits", lambda g: set(hit))             # the fake hit signal: a set of players
    music.tick(g)                                                      # a peace track first
    return server, g, now, hit


def played(server, start, team="p1"):
    return [c.split()[1] for c in server.log[start:] if c.startswith("playsound") and f"team={team}]" in c]


def step(g, now, seconds):
    for _ in range(int(seconds)):                                      # one tick per second, as the reads
        now[0] += 1
        music.tick(g)


def test_a_hit_switches_to_battle_once_and_the_calm_back_to_peace(monkeypatch):
    server, g, now, hit = setup(monkeypatch)
    calm = BATTLE[0]["calm"]
    start = len(server.log)
    hit.add(1)
    step(g, now, 1)
    assert played(server, start) == [BATTLE[0]["name"]]
    assert server.log[-2] == "stopsound @a[team=p1] music"
    start = len(server.log)
    step(g, now, calm - 1)                                             # more hits: no new command
    assert played(server, start) == []
    hit.clear()
    step(g, now, calm - 1)                                             # a short pause keeps the battle track
    assert played(server, start) == []
    step(g, now, 2)
    assert played(server, start) == [music.PEACE[1 % len(music.PEACE)]["name"]]
    start = len(server.log)
    step(g, now, calm * 2)                                             # peace stays without a hit
    assert played(server, start) == []
    hit.add(1)
    step(g, now, 1)                                                    # the next fight: the next battle track
    assert played(server, start) == [BATTLE[1]["name"]]


def test_a_hit_of_another_player_does_not_change_the_music(monkeypatch):
    server, g, now, hit = setup(monkeypatch)
    start = len(server.log)
    hit.add(2)
    step(g, now, 5)
    assert played(server, start) == []


def test_the_signal_reads_the_teams_of_the_plugin_answer():
    class G:
        paper = True

        @staticmethod
        def command(c):
            return "Hits: p1 p3" if c == "aoe hits" else ""
    assert music.hits(G) == {1, 3}
    G.command = staticmethod(lambda c: "Hits:")
    assert music.hits(G) == set()
    G.paper = False                                                    # a vanilla server: no plugin, no hits
    assert music.hits(G) == set()


@pytest.mark.mc
def test_the_plugin_names_the_team_of_a_unit_that_an_enemy_hits(tiny_world, tmp_path):
    from test_damage import health
    from test_paper import paper_reachable

    from game import combat, run
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a floor in the air, as tests/test_alerts.py
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon zombie 48.5 {y} 28.5 {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')
        game.command("team join p1 @e[tag=e]")
        game.command("aoe stats @e[tag=e,limit=1] 1000 4 0 1 0 infantry - 20")
        assert game.command("aoe hits").strip() == "Hits:"             # no hit yet
        for c in combat.building(combat.target_uuid([20, 20, 36, 36]), "CASTLE", 2, (20, y, 20, 35, y + 40, 35)):
            game.command(c)                                            # a castle of player 2 shoots the unit
        end = time.time() + 20
        while health(game, "e") >= 1000:
            assert time.time() < end, "the castle did not shoot"
            time.sleep(0.2)
        assert game.command("aoe hits").strip() == "Hits: p1"
        assert game.command("aoe hits").strip() == "Hits:"             # each call clears the hits
