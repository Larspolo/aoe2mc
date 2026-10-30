"""Live replay on Paper: a villager gathers only when its entity is at its resource, not while the Minecraft path
finder still walks it there (#766)."""
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_gather import TREE, VIL, hits, order  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Late(Fake):
    """The entity answers a far position to the first `late` position checks, then the position of the replay."""
    def __init__(self, late):
        super().__init__()
        self.late, self.checks, self.replay = late, 0, None

    def command(self, cmd):
        super().command(cmd)
        if cmd.startswith("data get entity u1 Pos"):
            self.checks += 1
            x, y, z = (0.5, 70.0, 0.5) if self.checks <= self.late else self.replay.units[7].pos
            return f"Villager has the following entity data: [{x}d, {y}d, {z}d]"
        return ""


def play(late, end=60000):
    d = data([order(0, 20), dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += [VIL, TREE]
    now, game = [0.0], Late(late)

    def sleep(s):
        now[0] += s
    r = game.replay = replay.Replay(game, d, ai=True)
    r.run(clock=lambda: now[0], sleep=sleep, log=None)
    return r, game


def test_the_first_wood_waits_for_the_entity():
    _, on_time = play(0)
    r, game = play(5)
    first = next(k for k, c in enumerate(game.sent) if c.startswith("particle") and "oak_log" in c)
    checks = [k for k, c in enumerate(game.sent) if c.startswith("data get entity u1 Pos")]
    assert len(checks) == 6 and checks[-1] < first                     # 5 far answers, then the entity is there
    assert len(hits(on_time.sent, "oak_log")) - 5 <= len(hits(game.sent, "oak_log")) < len(hits(on_time.sent, "oak_log"))
    assert 7 not in r.arriving


def test_a_unit_that_does_not_come_goes_there_with_tp():
    r, game = play(10 ** 6, end=90000)
    tp = "tp u1 {} {} {}".format(*r.units[7].pos)
    assert tp in game.sent and game.sent.index(tp) < next(k for k, c in enumerate(game.sent) if "oak_log" in c)
    assert game.checks < 30                                             # it stands: a new walk, then /tp (#2709)


def test_a_new_move_ends_the_wait():
    r, _ = play(10 ** 6, end=5000)
    r.move(dict(time=6000, player=1, kind="move", objects=[7], tile=[2.5, 2.5], names=["VILLAGER_MALE"]))
    assert 7 not in r.arriving and 7 not in r.working


@pytest.mark.mc
def test_a_replay_villager_chops_next_to_its_tree_in_the_forest(tmp_path):
    """The sample record: villager 9935 gets an ORDER on the oak at tile 76.5 49.5 in a forest at 2:15 (#718). The
    Minecraft path down the hill is slower than the AoE2 walk: its first wood must wait for it."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import math
    import re

    import combat
    import gather
    import run

    import aoe2mc
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(os.path.join(ROOT, "samples", "de-64.3.aoe2record"), str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        d = json.load(f)
    d["timeline"] = [e for e in d["timeline"] if e["time"] <= 200000]
    seen = {}
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, d)
        r = replay.Replay(game, d, ai=True)
        steps = r.steps

        def watch(t):                                               # the entity when the first wood of 9935 comes
            out = steps(t)
            v = r.units.get(9935)
            if v and "pos" not in seen and v.load > 0:
                m = re.findall(gather.NUMBER, game.command(f"data get entity {v.uuid} Pos").rsplit(":", 1)[-1])
                seen["pos"], seen["replay"] = tuple(map(float, m)), v.pos
            return out
        r.steps = watch
        r.run(4.0, log=None)
    shutil.rmtree(tmp_path / "W", ignore_errors=True)
    assert "pos" in seen, "no wood for villager 9935"
    (x, _, z), (rx, _, rz) = seen["pos"], seen["replay"]
    assert math.dist((x, z), (rx, rz)) <= replay.NEAR, (seen, "the entity is not at its tree")
