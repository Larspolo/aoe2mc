"""Live replay: a DELETE of a start building kills its combat target entity too (#3037). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_delete import delete  # noqa: E402

FOOTPRINT = [40, 8, 56, 24]                                  # block footprint: x0, z0, x1, z1 (replay.starts: x0, x1, z0, z1)
TARGET = combat.target_uuid([40, 8, 56, 24])


def castle(ai):
    d = data([], n=128)
    d["players"]["2"]["arch"] = "western"
    d["objects"] = [{"kind": "building", "ref": 21, "player": 2, "name": "CASTLE", "footprint": FOOTPRINT}]
    return replay.Replay(Fake(), d, ai=ai)


def test_a_deleted_start_castle_loses_its_target_after_its_arrows():
    cmds = castle(ai=True).commands(delete(500, [21], names=["CASTLE"], player=2))
    k = cmds.index(f"kill {TARGET}")
    assert any(c.startswith(f"aoe arrows {TARGET}") for c in cmds[:k])   # the units come out first
    assert not any(c.startswith(f"aoe arrows {TARGET}") for c in cmds[k + 1:])


def test_without_the_plugin_a_deleted_start_castle_has_no_target_to_kill():
    cmds = castle(ai=False).commands(delete(500, [21], names=["CASTLE"], player=2))
    assert not any(c.startswith("kill ") for c in cmds)
