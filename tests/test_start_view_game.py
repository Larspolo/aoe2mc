"""A converted four_civs world and a game of two people: each person goes to the start view of its player (#3603)."""
import contextlib
import io
import json

import scenarios

import aoe2mc
from game import run


def make_game(starts, yaw):
    g = run.Game.__new__(run.Game)
    g.people, g.sides, g.kind, g.spectators, sent = 2, {}, "vanilla", frozenset(), []
    g.starts, g.yaw = starts, yaw
    g.command = sent.append
    return g, sent


def test_two_people_go_to_the_start_views_of_players_one_and_two(tmp_path):
    src = scenarios.four_civs(str(tmp_path / "s.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([src, str(tmp_path / "W"), "--mc-version", "26.3"])
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        starts, yaw = run.start_places(json.load(f))
    g, sent = make_game(starts, yaw)
    g.side("Alex")
    g.side("Steve")
    tp = {c.split()[1]: [float(v) for v in c.split()[2:5]] for c in sent if c.startswith("tp ")}
    for name, (tx, ty) in {"Alex": (22, 22), "Steve": (58, 22)}.items():
        x, y, z = tp[name]
        assert abs(x - tx * 4) <= 4 and abs(z - ty * 4) <= 4      # the block of the view tile, 4 blocks at most
        assert any(c.startswith(f"tp {name} ") and c.endswith(f" {yaw} 0") for c in sent)   # the yaw of aoe2mc.json
