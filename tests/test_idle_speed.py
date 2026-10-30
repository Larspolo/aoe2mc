"""Units walk at their AoE2 speed also without an order (#849): combat.setup sends the attribute movement_speed."""
import shutil
import time

import pytest
from test_unit_ai import data

from game import ai, combat, run


def test_setup_sends_the_walk_speed_of_each_unit():
    class Game:
        sent = []

        def command(self, c):
            self.sent.append(c)
            return "Stats: 1 units"
    data = {"tile_size": 4, "objects": [{"kind": "unit", "player": 1, "name": "LONGBOWMAN", "uuid": "a"},
                                        {"kind": "unit", "player": 2, "name": "PIKEMAN", "uuid": "p"},
                                        {"kind": "unit", "player": 0, "name": "DEER", "uuid": "d"}]}   # Gaia: vanilla
    combat.setup(Game(), data)
    speed = [c for c in Game.sent if "movement_speed" in c]
    assert speed == [f"attribute a minecraft:movement_speed base set {ai.movement_speed('LONGBOWMAN', 4)}",
                     f"attribute p minecraft:movement_speed base set {ai.movement_speed('PIKEMAN', 4)}"]


@pytest.mark.mc
def test_a_pikeman_without_an_order_walks_at_its_aoe2_speed(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 10} {z0 + 40}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 8} {y - 1} {z0 + 36} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        objects = []
        for tag, dz, team, name in (("a", 2, "p1", "LONGBOWMAN"), ("p", 21, "p2", "PIKEMAN")):   # 19 blocks apart
            kind = "skeleton" if tag == "a" else "zombie"
            game.command(f'summon {kind} {x0 + 3.5} {y} {z0 + dz + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            objects.append({"kind": "unit", "player": int(team[1]), "name": name, "uuid": f"@e[tag={tag},limit=1]"})
        assert combat.setup(game, {"tile_size": 4, "objects": objects}) == 2
        assert game.command("aoe attack @e[tag=a] @e[tag=p,limit=1]").strip() == "Attack: 1 units"
        track, end = [], time.time() + 20
        while time.time() < end:
            p = data(game, "p", "Pos")
            if p is None:
                break
            track.append((time.monotonic(), p[2]))
            if p[2] < z0 + 6:
                break
            time.sleep(0.1)
        z = z0 + 21.5
        mid = [(t, pz) for t, pz in track if z - 13 <= pz <= z - 3]       # walking, after the start and before the stop
        assert len(mid) >= 3, track
        v = (mid[0][1] - mid[-1][1]) / (mid[-1][0] - mid[0][0])
        assert abs(v - ai.walk_speed("PIKEMAN", 4)) <= 0.15 * ai.walk_speed("PIKEMAN", 4), (v, track)
