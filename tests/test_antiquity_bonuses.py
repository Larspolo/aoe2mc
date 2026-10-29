"""The Return of Rome civilization bonuses of the units and buildings of Antiquity Mode (#3827,
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
       "range": [train.stats(g("HITTITES", a), "TRIREME").range for a in range(4)]}}
print(json.dumps(out))
"""


@pytest.fixture(scope="module")
def antiquity():
    env = dict(os.environ, AOE2MC_RULES="antiquity")
    return json.loads(subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True, env=env,
                                     check=True).stdout)


def test_a_unit_bonus_works_in_antiquity_mode(antiquity):
    choson, roman = antiquity["legionary"]
    assert choson > roman                                                   # Choson Legionaries: more hit points
    assert all(a < b for a, b in zip(antiquity["range"], antiquity["range"][1:]))   # Hittite warships: range in each age


def test_a_building_bonus_works_in_antiquity_mode(antiquity):
    babylonian, roman = antiquity["tower"]
    assert babylonian > roman                                               # Babylonian towers: more hit points
    roman, shang = antiquity["house"]
    assert roman != shang and all(roman[k] <= v for k, v in shang.items())  # Roman buildings cost less
