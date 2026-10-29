"""The builders of the live replay build for the AoE2 build time before they gather again (#1282): a villager that
chops and gets a BUILD of a house stops its work, walks to the house and gathers nothing more; the builders of a
lumber camp chop next to it only after the build time; a jump gives the same wood as the play. Fake clock and RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import Fake, data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_gather import TREE, VIL, order  # noqa: E402
from test_replay_jump_team import CAMP, run  # noqa: E402

import build  # noqa: E402
import gather  # noqa: E402
import replay  # noqa: E402

VIL2 = dict(VIL, uuid="u2", ref=8, tile=[2.5, 11.5])
HOUSE = dict(time=60000, player=1, kind="build", type=70, name="HOUSE", tile=[10.0, 6.0], objects=[7],
             names=["VILLAGER_MALE"])
END = 150000
WOOD = gather.AOE2_WORK["wood"]
CAMP_MS = build.BUILD_TIMES["LUMBER_CAMP"] * 1000                  # the AoE2 build time of one villager


@pytest.mark.parametrize("ai", [False, True])
def test_a_house_builder_stops_chopping_and_walks_to_the_house(ai):
    r = run([order(0, 20), HOUSE], [TREE], ai, to=None)
    v, (x0, x1, z0, z1) = r.units[7], r.placed[-1][2]
    assert v.tree is None and 7 not in r.working and not r.builds
    assert v.cell in r.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
    assert 0 < r.gathered[1]["wood"] <= WOOD * 60 + 1                # nothing after the BUILD at 60 s


@pytest.mark.parametrize("n", [1, 2])
def test_camp_builders_chop_only_after_the_build_time(n):
    camp = dict(CAMP, time=1000, objects=[7, 8][:n], names=["VILLAGER_MALE"] * n)
    r = run([camp], [TREE, VIL2], to=None)
    work = CAMP_MS * 3 / (n + 2)                                      # AoE2: t × 3 / (n + 2)
    assert all(r.units[i].tree == (5, 10) for i in camp["objects"])
    assert 0 < r.gathered[1]["wood"] <= n * WOOD * (300000 - 1000 - work) / 1000 + n


@pytest.mark.parametrize("n", [1, 2])
def test_the_build_ends_at_the_aoe2_build_time(n):
    d = data([])
    d["objects"] += [VIL, VIL2, TREE]
    r = replay.Replay(Fake(), d)
    r.grid()
    r.commands(dict(CAMP, objects=[7, 8][:n], names=["VILLAGER_MALE"] * n))
    for i in (7, 8)[:n]:                                            # the walk to the camp, then t × 3 / (n + 2)
        assert r.builds[i][0] == pytest.approx(r.walk_end(r.units[i], 0) + CAMP_MS * 3 / (n + 2))
        assert r.builds[i][1]["resource"] == (5, 10) and r.units[i].tree is None


@pytest.mark.parametrize("timeline", [[order(0, 20), HOUSE], [dict(CAMP, time=1000)],
                                      [dict(CAMP, time=1000, objects=[7, 8], names=["VILLAGER_MALE"] * 2)]])
def test_a_jump_gives_the_wood_of_the_play(timeline):
    """To 150 s: the two builders do not use up the 100 wood of the tree (a jump has no cap of one resource, #1147)."""
    def wood(to):
        d = data(timeline + [dict(time=END, player=1, kind="chat", text="end")])
        d["objects"] += [VIL, VIL2, TREE]
        game = Clock()
        r = replay.Replay(game, d)
        r.run(clock=lambda: game.now, sleep=game.sleep, log=None, to=to)
        return r.gathered[1]["wood"]
    play, jump = wood(None), wood(END)
    assert play > 0 and jump == pytest.approx(play, rel=0.1)
