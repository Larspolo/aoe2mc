"""The Return of Rome civilization bonuses of the units and buildings and the missing items of Antiquity Mode (#3827,
docs/research/antiquity.md, 1.6). The checks run in one child process with AOE2MC_RULES=antiquity."""
import json
import os
import subprocess
import sys

import pytest

GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game")
CODE = f"""
import json, sys, types
sys.path.insert(0, {GAME!r})
import build, civs, combat, train
g = lambda civ, age=0: types.SimpleNamespace(data={{"players": {{"1": {{"civ": civ}}}}}}, player=1, techs=set(build.AGE_TECHS[:age]))
out = {{"legionary": [train.stats(g(c), "LEGIONARY").hp for c in ("CHOSON", "ROMANS")],
       "tower": [civs.hp(c, "WATCH_TOWER", combat.BUILDINGS["WATCH_TOWER"]).hp for c in ("BABYLONIANS", "ROMANS")],
       "house": [build.price(g(c), "HOUSE") for c in ("ROMANS", "SHANG")],
       "range": [train.stats(g("HITTITES", a), "TRIREME").range for a in range(4)],
       "missing": {{t: civs.MISSING.get(t, []) for t in ("SLINGER", "TEMPLE", "ACADEMY")}}}}
print(json.dumps(out))
"""


@pytest.fixture(scope="module")
def antiquity():
    env = dict(os.environ, AOE2MC_RULES="antiquity")
    return json.loads(subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True, env=env,
                                     check=True).stdout)


def test_a_unit_bonus_works_in_antiquity_mode(antiquity):
    choson, roman = antiquity["legionary"]
    assert choson == roman + 80                                             # Choson Legionaries +80 hit points
    assert antiquity["range"] == [antiquity["range"][0] + n for n in range(4)]   # Hittite warships +1/+2/+3 range


def test_a_building_bonus_works_in_antiquity_mode(antiquity):
    babylonian, roman = antiquity["tower"]
    assert babylonian == round(roman * 1.6)                                 # Babylonian towers +60 % hit points
    roman, shang = antiquity["house"]
    assert {k: int(v * 0.9 + 0.5) for k, v in shang.items()} == roman       # Roman buildings -10 %


def test_each_civilization_misses_the_items_of_the_wiki(antiquity):
    assert antiquity["missing"] == {"SLINGER": ["ASSYRIANS", "HITTITES"], "TEMPLE": ["MACEDONIANS"],
                                    "ACADEMY": ["PERSIANS"]}
