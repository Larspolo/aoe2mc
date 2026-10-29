"""The production panel of the live replay with a recorded game: a unit in training and a research (#2811, #2807)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import aoe2mc  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
TOWN_CENTER = 1652          # player 2, at 92, 29: the first villager queue (0:00.9) and the Loom (6:34.6)
UNIT_TIME = 936 + aoe2mc.train_ms("VILLAGER_MALE") // 2   # ms: the first villager (from 936 ms) is half done
RESEARCH_TIME = 470000      # ms: the Loom of the town center is in research (from 464077 ms, after the villagers)


def make():
    d = data(aoe2mc.read_timeline(REC), n=480)
    d["objects"] = aoe2mc.read_record(REC)[5]
    for o in d["objects"]:                      # the converter gives the start buildings a footprint (4 × 4 tiles, T = 4)
        if o.get("ref") == TOWN_CENTER:
            o["kind"], o["footprint"] = "building", [360, 108, 376, 124]
    d["players"]["2"]["arch"] = "western"       # data() has "meso", which buildings.ARCH lacks
    return replay.Replay(Fake(), d)


def panel_of(r, t):
    return [c for c in r.panel(t) if c.startswith("summon") and f"aoe2mc.panel.{TOWN_CENTER}" in c]


def test_a_unit_in_training_shows_its_name_and_a_progress_bar():
    (summon,) = panel_of(make(), UNIT_TIME)
    assert r'Villager \u00d74 [|||||.....]' in summon     # json.dumps escapes the count sign


def test_a_research_in_the_same_building_names_the_technology():
    (summon,) = panel_of(make(), RESEARCH_TIME)
    assert '"text": "Loom [' in summon
