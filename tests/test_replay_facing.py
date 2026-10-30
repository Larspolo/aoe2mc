"""Live replay: a working villager faces the middle of its resource at each gather step, and on Paper its walk
order ends at its first step, so that no brain turns it away (#867)."""
import json
import math
import os
import re
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay_gather import TREE, order, play  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize("ai", [False, True])
def test_each_step_faces_the_middle_of_the_tree(ai):
    r, sent = play([order(0, 20)], TREE, 60000, ai)
    x0, x1, z0, z1 = r.map.feet.get((5, 10), (20, 24, 40, 44))
    turns = [c.split()[3:6] for c in sent if c.startswith("rotate u1 facing")]
    assert len(turns) > 15
    assert {(float(x), float(z)) for x, _, z in turns} == {((x0 + x1) / 2, (z0 + z1) / 2)}
    stops = [k for k, c in enumerate(sent) if c == "aoe stop u1"]
    first = next(k for k, c in enumerate(sent) if c.startswith("particle") and "oak_log" in c)
    assert stops == ([stops[0]] if ai else []) and (not ai or stops[0] < first)   # once, at the first step


@pytest.mark.mc
def test_replay_villagers_face_their_resource_on_paper(tmp_path):
    """The sample record to 4:20 at speed 4: before each gather step (the last rotate was one step ago) each
    working villager faces the middle of its resource, within 30°."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io

    import combat
    import run

    import aoe2mc
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(os.path.join(ROOT, "samples", "de-64.3.aoe2record"), str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        d = json.load(f)
    d["timeline"] = [e for e in d["timeline"] if e["time"] <= 260000]
    off, n = [], [0]
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, d)
        r = replay.Replay(game, d, ai=True)
        work = gather.Gather.work

        def watch(self, v):
            rot = re.findall(gather.NUMBER, game.command(f"data get entity {v.uuid} Rotation").rsplit(":", 1)[-1])
            pos = re.findall(gather.NUMBER, game.command(f"data get entity {v.uuid} Pos").rsplit(":", 1)[-1])
            if v.load > 1 and len(rot) == 2 and len(pos) == 3 and v.tree not in r.map.farms:
                T, (tx, tz) = r.T, v.tree
                x0, x1, z0, z1 = r.map.feet.get(v.tree, (tx * T, tx * T + T, tz * T, tz * T + T))
                x, z = float(pos[0]), float(pos[2])
                want = math.degrees(math.atan2(-((x0 + x1) / 2 - x), (z0 + z1) / 2 - z))
                n[0] += 1
                if abs((float(rot[0]) - want + 180) % 360 - 180) >= 30:
                    off.append((v.uuid, v.load, rot[0], round(want)))
            work(self, v)
        gather.Gather.work = watch
        try:
            r.run(4.0, log=None)
        finally:
            gather.Gather.work = work
    shutil.rmtree(tmp_path / "W", ignore_errors=True)
    assert n[0] > 40, n
    assert not off, off
