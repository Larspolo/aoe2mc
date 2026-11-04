"""#5666 (epic #5119): the #includeXS file of a random map script goes into aoe2mc.json with --xs FILE, and the game
program runs it in the mode of the random map."""
import contextlib
import io
import json
import os
import sys

from test_rmap import SCRIPT

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402

XS = 'int n = 0;\nvoid main() { n = n + 1; }\n'


def world(tmp_path, xs=None, include=True):
    src = tmp_path / "m.rms"
    src.write_text(SCRIPT.replace("<LAND_GENERATION>", "#includeXS triggers.xs\n<LAND_GENERATION>", 1) if include else SCRIPT)
    if xs:
        (tmp_path / "triggers.xs").write_text(xs)
    out, err = io.StringIO(), io.StringIO()
    folder = tmp_path / ("W" + str(include) + str(bool(xs)))
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        aoe2mc.convert(str(src), str(folder), map_size=40, with_units=False,
                       xs=str(tmp_path / "triggers.xs") if xs else None)
    with open(folder / "aoe2mc.json") as f:
        return json.load(f), out.getvalue() + err.getvalue()


def test_xs_file_goes_into_the_world(tmp_path):
    data, _ = world(tmp_path, xs=XS)
    assert data["xs_script"] == ["triggers", XS]


def test_no_xs_gives_one_warning_and_the_same_land(tmp_path):
    data, out = world(tmp_path)
    lines = [line for line in out.splitlines() if "triggers.xs" in line]
    assert len(lines) == 1 and "--xs FILE" in lines[0] and "xs_script" not in data
    plain, _ = world(tmp_path, include=False)
    assert data["players"] == plain["players"]


def test_main_runs_at_the_first_tick_of_a_random_map_game():
    _, g, _ = game({"0": {}, "1": {}, "2": {}})
    g.mode = "random-map"
    g.data["xs_script"] = ["triggers", XS]
    g.clock, g.t0 = (lambda: 1.0), 0.0
    scenario.script(g)
    scenario.xs(g)
    assert g.xs.get("n") == 1
