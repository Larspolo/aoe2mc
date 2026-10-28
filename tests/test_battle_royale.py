"""#2439: `run.py --play --mode battle-royale` has the Corruption of the AoE2 DE game mode "Battle Royale" (wiki "Battle
Royale"): it takes the map from its border to its center and destroys each unit and building that it touches. The
world border shows it; the game program destroys what is outside, as the border hurts only players."""
import os
import re
import shutil
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import battle_royale  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402


def fake(map_size=24, T=4):
    log = []
    return types.SimpleNamespace(data={"map_size": map_size}, map=types.SimpleNamespace(T=T, n=map_size * T),
                                 ended=None, command=lambda c: log.append(c) or "", log=log)


def boxes(cmds):
    """The (x0, z0, x1, z1) of the volume selectors of the kill commands."""
    out = []
    for c in cmds:
        if c.startswith("kill"):
            x, z, dx, dz = (float(re.search(f"{k}=(-?[0-9.]+)", c)[1]) for k in ("x", "z", "dx", "dz"))
            out.append((x, z, x + dx, z + dz))
    return out


def test_setup_puts_the_border_on_the_map_square():
    g = battle_royale.setup(fake())
    assert g.log[:3] == ["worldborder center 48.0 48.0", "worldborder damage buffer 0", "worldborder set 96.0"]
    assert "30:00" in g.log[3]


def test_the_border_reaches_the_center_after_the_time():
    g = battle_royale.setup(fake())
    for t, w in ((0, 96.0), (15 * 60, 48.0), (30 * 60, 0.0), (40 * 60, 0.0)):
        g.corruption_time = t
        assert battle_royale.width(g) == pytest.approx(w)


def test_a_tick_moves_the_border_and_destroys_outside_it():
    g = battle_royale.setup(fake())
    g.log.clear()
    battle_royale.tick(g, 15 * 60)
    assert g.log[0] == "worldborder set 48.0"
    assert sum(c.startswith("aoe destroy @e[tag=aoe2mc.building,") for c in g.log) == 4
    west, east, north, south = boxes(g.log)
    assert west[2] <= 24 and east[0] == 72 and north[3] <= 24 and south[1] == 72   # the square 24..72 stays
    assert north[0] == south[0] == 24 and north[2] == south[2] == 72
    assert all(f"team=!,type=!player," in c for c in g.log if c.startswith("kill"))
    g.log.clear()
    battle_royale.tick(g, 1.0)                                    # less than EVERY seconds later: no command
    assert g.log == []


def test_an_ended_game_sends_nothing():
    g = battle_royale.setup(fake())
    g.log.clear()
    g.ended = "Victory"
    battle_royale.tick(g, 60)
    assert g.log == []


def test_the_run_loop_moves_the_border_only_in_battle_royale(monkeypatch):
    calls = []
    for m in (gather.conquest, gather.fog, gather.herd):
        monkeypatch.setattr(m, "tick", lambda g, m=m: calls.append(m.__name__))
    monkeypatch.setattr(gather.battle_royale, "tick", lambda g, dt: calls.append("battle_royale"))
    for m in (gather.wonder, gather.relic_victory, gather.treaty):
        monkeypatch.setattr(m, "tick", lambda g, dt: None)
    monkeypatch.setattr(gather.score, "tick", lambda g: None)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    for mode, n in (("standard", 0), ("battle-royale", 3)):
        calls.clear()
        g = object.__new__(gather.Gather)
        g.tick, g.bots, g.ended, g.mode = 0.25, (), None, mode
        g.point = g.step = lambda: None
        g.clicks = lambda: ()
        g.run(until=lambda: calls.count("conquest") >= 3)
        assert calls.count("battle_royale") == n


def test_the_mode_option_goes_to_play(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    seen = {}
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(start=lambda: None, stop=lambda: None,
                                                                         port=0))
    monkeypatch.setattr(run, "play", lambda *a, **k: seen.update(k) or types.SimpleNamespace(ended=None))
    monkeypatch.setattr(run, "console", lambda game: None)
    run.main([str(tmp_path), "--play", "--mode", "battle-royale"])
    assert seen["mode"] == "battle-royale"


@pytest.mark.mc
def test_the_corruption_kills_the_units_outside_the_border_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.command("forceload add 0 0 95 95")
        game.command("fill 0 199 0 95 199 95 stone_bricks")
        game.command("team add p1")
        for tag, x, z in (("out", 10.5, 48.5), ("in", 48.5, 48.5), ("south", 48.5, 90.5)):
            game.command(f'summon zombie {x} 200 {z} {{NoAI:1b,PersistenceRequired:1b,Tags:["{tag}"]}}')
        game.command("team join p1 @e[type=zombie]")
        g = fake()
        g.command = game.command
        battle_royale.setup(g)
        battle_royale.tick(g, 15 * 60)                            # the border is 24..72 now
        time.sleep(0.5)
        alive = {t for t in ("out", "in", "south") if "passed" in game.command(f"execute if entity @e[tag={t}]")}
        assert alive == {"in"}
        assert "48 block" in game.command("worldborder get")
