"""Record Game (#3045): each menu item writes its right event, a unit a "queue" with its AoE2 type, a technology a
"research"."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import record  # noqa: E402
import replay  # noqa: E402
import train  # noqa: E402
from test_record_game import world  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def events(tmp_path, names):
    """The timeline of the queue of each name in the town center of world()."""
    g = types.SimpleNamespace(data=world(), player=1, map=types.SimpleNamespace(T=4))
    path = str(tmp_path / "menu.jsonl")
    record.start([g], path)
    for name in names:
        record.queued(g, name, (8, 24, 8, 24))
    g.record.f.close()
    return record.load(path)[1]


def test_a_trade_cart_is_a_queue_of_its_aoe2_type(tmp_path):
    e, = events(tmp_path, ["TRADE_CART"])
    assert e["kind"] == "queue" and e["type"] == 128 and e["name"] == "TRADE_CART"


def test_a_keep_is_a_research(tmp_path):
    e, = events(tmp_path, ["KEEP"])
    assert e["kind"] == "research" and e["technology"] == "Keep"


def test_each_unit_of_the_menu_is_a_queue_event(tmp_path):
    units = [r["name"] for r in train.ROWS if r["name"] not in train.TECHS and not r["name"].endswith("_AGE")]
    timeline = events(tmp_path, units)
    assert [e["kind"] for e in timeline] == ["queue"] * len(units)
    assert [e["name"] for e in timeline] == units


def test_a_queued_cart_is_trained_by_the_replay(tmp_path):
    e, = events(tmp_path, ["TRADE_CART"])
    spawn, = replay.Replay(Fake(), data([e])).spawns()
    assert spawn["name"] == "TRADE_CART" and spawn["type"] == 128
