"""A town center and a castle shoot arrows at the enemy units in their range (#1111): combat.building and the plugin."""
import shutil
import time

import pytest
from test_damage import health

from game import combat, run


def test_building_command_has_the_attack():
    uuid = "00000000-0000-0000-0000-000000000001"
    box = (8, 64, 8, 23, 104, 23)
    s = combat.stats("TOWN_CENTER")
    tc, = [c for c in combat.building(uuid, "TOWN_CENTER", 1, box) if c.startswith("aoe building")]
    assert tc.startswith(f"aoe building {uuid} {s.hp} {s.melee} {s.pierce} 8 64 8 23 104 23 {s.attack} {s.range * 4} "
                         f"{round(s.reload / combat.NORMAL * 20)} 0 ")    # range: tiles × 4; reload: ticks; no minimum
    c = combat.stats("CASTLE")
    castle, = [c for c in combat.building(uuid, "CASTLE", 1, box, T=2) if c.startswith("aoe building")]
    assert f" {c.attack} {c.range * 2} {round(c.reload / combat.NORMAL * 20)} {combat.FORT_MIN_RANGE['CASTLE'] * 2} " in castle   # (#1546)
    h = combat.stats("HOUSE")
    house, = [c for c in combat.building(uuid, "HOUSE", 1, box) if c.startswith("aoe building")]
    assert house == f"aoe building {uuid} {h.hp} {h.melee} {h.pierce} 8 64 8 23 104 23"   # no attack: no arrows


@pytest.mark.mc
def test_town_center_shoots_the_enemy_in_range(tiny_world, tmp_path):
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
        # tag: (x, z, team). e: an enemy 12 blocks from the edge (range 24); o: an own militia next to it;
        # f: an enemy 30 blocks from the edge, out of the range
        units = {"e": (48.5, 28.5, "p2"), "o": (28.5, 48.5, "p1"), "f": (66.5, 66.5, "p2")}
        for tag, (x, z, team) in units.items():
            game.command(f'summon zombie {x} {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "MILITIA")).strip() == "Stats: 1 units"
        game.command("aoe stats @e[tag=e,limit=1] 1000 4 0 1 0 infantry - 20")    # pierce armor 1, many hit points
        assert health(game, "e") == 1000.0
        for c in combat.building(uuid, "TOWN_CENTER", 1, box, inside=["VILLAGER"]):   # 1 arrow (#1201); after the units
            game.command(c)
        hp = []
        while len(hp) < 30 and (not hp or hp[-1] == 1000.0):
            hp.append(health(game, "e"))
            time.sleep(0.1)
        h0, t0 = health(game, "e"), time.time()
        arrow = combat.stats("TOWN_CENTER").attack - 1                         # per arrow: attack - pierce 1
        assert h0 < 1000 and (1000 - h0) % arrow == 0, hp
        time.sleep(6)
        h1, dt = health(game, "e"), time.time() - t0
        shots = (h0 - h1) / arrow
        assert shots == int(shots), (h0, h1)
        assert 0.6 * dt / 1.2 <= shots <= dt / 1.2 + 1.5, (h0, h1, dt)        # one arrow each 2 AoE2 s (1.2 s)
        full = combat.stats("MILITIA").hp
        assert (health(game, "o"), health(game, "f")) == (full, full)       # not the own unit, not out of range
