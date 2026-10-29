"""Writing in Antiquity Mode (#3920, epic #3887; AoE wiki "Writing"): the allies of a player see for it only after it
researched Writing, as in Return of Rome. The rule modules read their data at import, so the check runs in a child
process."""
import json

from test_antiquity_setting import child
from test_fog_units import E1, E2

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_shared_exploration import game, update
import fog
g, ally, foe = game()
out = {"before": [fog.shares(g, ally), update(g)]}
ally.techs = {"WRITING"}
g.sent.clear()
out["after"] = [fog.shares(g, ally), fog.shares(g, foe), update(g)]
print(json.dumps(out))
'''


def test_an_ally_sees_for_the_player_only_after_its_writing():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["before"] == [False, [f"aoe hide @a[team=p1] {E1} {E2}"]]   # E1 is near the ally only
    assert out["after"] == [True, False, [f"aoe show @a[team=p1] {E1}"]]
