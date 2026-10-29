"""A damaged building wears in stages (#1522, AoePlugin.java wear): at each 1/7 of its hit points below full (6 stages,
#1650) a fixed random share of its blocks above the floor is worn (cracked or mossy bricks, stripped logs, broken windows) or gone
(holes, cobwebs at the last stage), more at each stage. The blocks go anywhere in the building, not from the top as a
construction site (build.rise). A repair puts the blocks of each stage back. Barriers and block entities stay."""
import re
import shutil
import time

import pytest

from game import combat, run

NAMES = ("air", "cobweb", "cracked_stone_bricks", "stone_bricks", "stripped_oak_log", "oak_log", "glass", "barrier",
         "chest", "oak_planks")


def blocks(game, box):
    """{(x, y, z): block name of NAMES} of the box."""
    x0, y0, z0, x1, y1, z1 = box
    out = {}
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                out[x, y, z] = next((n for n in NAMES if "passed" in game.command(f"execute if block {x} {y} {z} {n}")),
                                    "other")
    return out


def settle(game, box, last, seconds=5):
    """The blocks of the box after the next burn cycles (each second) changed them, or as they are."""
    end = time.time() + seconds
    while time.time() < end:
        time.sleep(1.2)
        now = blocks(game, box)
        if now != last:
            time.sleep(1.2)                                            # the change is done in one cycle
            return blocks(game, box)
    return blocks(game, box)


def changed(a, b):
    return {p for p in a if a[p] != b[p]}


@pytest.mark.mc
def test_a_building_wears_in_six_stages_and_a_repair_puts_the_blocks_back(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    box = (8, y, 8, 15, y + 5, 15)                                     # 8 x 8, the floor at y, walls up to y + 4
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command(f"fill 0 {y - 1} 0 23 {y - 1} 23 stone")
        game.command(f"fill 8 {y} 8 15 {y} 15 stone_bricks")           # the floor
        game.command(f"fill 8 {y + 1} 8 15 {y + 4} 15 stone_bricks hollow")
        game.command(f"fill 9 {y + 1} 9 14 {y + 3} 14 barrier")        # the free space inside
        game.command(f"fill 8 {y + 5} 8 15 {y + 5} 15 oak_planks")     # the roof
        for x, z in ((8, 8), (8, 15), (15, 8), (15, 15)):
            game.command(f"fill {x} {y + 1} {z} {x} {y + 4} {z} oak_log")
        game.command(f"fill 11 {y + 2} 8 12 {y + 3} 8 glass")
        game.command(f"setblock 10 {y + 1} 10 chest")
        game.command("team add p2")
        uuid = combat.target_uuid([8, 8, 16, 16])
        for c in combat.building(uuid, "HOUSE", 2, box):
            game.command(c)
        start = len(game.server.log)
        full = blocks(game, box)
        assert full[10, y + 1, 10] == "chest" and full[9, y + 1, 9] == "barrier"
        stages = [full]
        top = combat.BUILDINGS["HOUSE"].hp
        for hp in (round(top * f) for f in (0.82, 0.69, 0.55, 0.40, 0.27, 0.11)):   # one in each stage
            game.command(f"scoreboard players set {uuid} aoe_hp {hp}")
            stages.append(settle(game, box, stages[-1]))
        gone = [sum(b[p] in ("air", "cobweb") and full[p] != "air" for p in b) for b in stages]
        worn = [sum(b[p] in ("cracked_stone_bricks", "stripped_oak_log") for p in b) for b in stages]
        assert gone[0] == worn[0] == 0
        assert 0 < gone[1] and all(a < b for a, b in zip(gone[1:], gone[2:])) and 0 < worn[1], (gone, worn)
        assert all(changed(full, a) < changed(full, b) for a, b in zip(stages[1:], stages[2:]))   # more at each stage
        for b in stages:
            assert all(b[p] == full[p] for p in b if full[p] in ("barrier", "chest") or p[1] == y)   # also the floor
        for b in stages[1:]:
            holes = {p[1] for p in changed(full, b) if b[p] in ("air", "cobweb")}
            assert min(holes) <= y + 2 and max(holes) == y + 5            # not from the top only, as a construction site
        assert "cobweb" in stages[-1].values() and "cobweb" not in stages[-2].values()
        game.command(f"scoreboard players set {uuid} aoe_hp {round(top * 0.55)}")   # a repair to 55 %: stages 4-6 back
        assert settle(game, box, stages[-1]) == stages[3]
        game.command(f"scoreboard players set {uuid} aoe_hp {top}")    # full
        assert settle(game, box, stages[3]) == full
        errors = [ln for ln in game.server.log[start:] if re.search(r"Exception|/ERROR\]|Could not pass event", ln)
                  and "minecraftservices.com" not in ln]                   # no Mojang hosts here: not the plugin
        assert not errors, errors
