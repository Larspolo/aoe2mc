"""Live replay: GARRISON and UNGARRISON on a building that the replay placed (a new object ID, #876). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_garrison import vil  # noqa: E402

import aoe2mc  # noqa: E402

TC = 621                     # a recorded game builds a town center with the old ID of the DE data file


def play(timeline, end):
    d = data(timeline + [dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += [vil(7, "u1", [2.5, 10.5]), vil(8, "u2", [2.5, 11.5])]
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d)
    r.run(clock=lambda: now[0], sleep=sleep, log=None)
    return r, game.sent


def test_a_record_builds_a_town_center():
    assert aoe2mc.object_kinds()[TC] == ("B", "TOWN_CENTER")
    assert TC not in aoe2mc.object_kinds(old=False)                 # read_scx maps it to the DE ID itself


def test_name_timeline_names_the_new_target():
    tl = [dict(time=0, player=1, kind="build", type=TC, name="TOWN_CENTER", tile=[8.0, 8.0], objects=[7]),
          dict(time=60000, player=1, kind="queue", objects=[100], name="VILLAGER_MALE"),
          dict(time=90000, player=1, kind="garrison", objects=[7], target=100)]
    aoe2mc.name_timeline([{"ref": 7, "name": "VILLAGER_MALE"}], tl)
    assert tl[2]["target_name"] == "TOWN_CENTER" and "target_name" not in tl[1]


def test_units_go_into_a_new_town_center_and_come_out():
    build = dict(time=0, player=1, kind="build", type=TC, tile=[8.0, 8.0])
    garrison = dict(time=1000, player=1, kind="garrison", objects=[7, 8], target=100, target_name="TOWN_CENTER",
                    names=["VILLAGER_MALE"] * 2)
    r, sent = play([build, garrison], 40000)
    rect = r.placed[-1][2]
    assert r.placed[-1][1] == "TOWN_CENTER" and r.garrisons == {rect: [7, 8]} and r.ids == {100: rect}
    assert "tag u1 add aoe2mc.garrisoned" in sent and "tag u2 add aoe2mc.garrisoned" in sent
    out = dict(time=40000, player=1, kind="ungarrison", objects=[100], names=["TOWN_CENTER"])
    r, sent = play([build, garrison, out], 50000)
    assert r.garrisons == {} and "tag u1 remove aoe2mc.garrisoned" in sent


def test_the_click_tile_picks_the_building():
    builds = [dict(time=0, player=1, kind="build", type=TC, tile=[4.0, 4.0]),
              dict(time=0, player=1, kind="build", type=TC, tile=[12.0, 12.0])]
    r, _ = play(builds, 1000)
    first, second = (p[2] for p in r.placed)
    e = dict(kind="order", player=1, target=200, target_name="TOWN_CENTER", tile=[4.2, 3.9])
    assert r.holder(e)[0] == first and r.holder(dict(e, tile=None))[0] == first      # the same ID: the same building
    assert r.holder(dict(e, target=201, tile=None))[0] == second                    # the newest free one
    assert r.holder(dict(e, target_name="HOUSE")) is None
