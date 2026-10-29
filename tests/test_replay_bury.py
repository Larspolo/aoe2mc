"""Live replay: a builder that died in a fight ends its build without an error (bury(), #3943). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, build, data  # noqa: E402


def test_a_dead_builder_ends_its_build():
    d = data([])
    d["objects"] = [{"kind": "unit", "name": "VILLAGER_FEMALE", "player": 1, "tile": [6.5, 6.5],
                     "uuid": "1dcc6967-173c-2031-ccae-9650ba134730", "ref": 7}]
    r = replay.Replay(Fake(), d)
    r.commands(dict(build(), objects=[7], names=["VILLAGER_FEMALE"]))
    assert 7 in r.builds
    r.bury(1)                                       # Fake finds no entity: the villager died
    assert 7 not in r.units and 7 not in r.builds
    r.steps(10 ** 6)
