"""Alchemy of Antiquity Mode (#3980): the Fire Galley and the Bowman get more attack, as in Return of Rome; the War
Galley keeps its attack. The rule modules read their data at import, so the check runs in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
import combat, train
out = {}
for n in ("FIRE_GALLEY", "BOWMAN", "WAR_GALLEY"):
    s = combat.stats(n)
    out[n] = [s.attack, train.TECHS["ALCHEMY"](n, s).attack]
print(json.dumps(out))
'''


def test_alchemy_gives_the_fire_galley_and_the_bowman_more_attack():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["FIRE_GALLEY"][1] > out["FIRE_GALLEY"][0] and out["BOWMAN"][1] > out["BOWMAN"][0]
    assert out["WAR_GALLEY"][1] == out["WAR_GALLEY"][0]
