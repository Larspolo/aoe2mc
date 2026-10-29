"""Fanaticism of Antiquity Mode (#3987): after it, a priest rests less long after a conversion. The rule modules read
their data at import, so the check runs in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_theocracy import group
out = {}
for techs in ((), ("FANATICISM",)):
    g = group(*techs)
    out[",".join(techs)] = {k: g.faith[k] for k in ("m0", "m1", "m2")}
print(json.dumps(out))
'''


def test_fanaticism_shortens_the_rest_of_the_priests():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    before, after = out[""], out["FANATICISM"]
    for k in ("m0", "m1", "m2"):
        assert 0 < after[k] < before[k], k
