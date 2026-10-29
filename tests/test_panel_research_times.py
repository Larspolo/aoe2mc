"""The production panel of the live replay shows each research of the record, also outside the town center: the
research seconds come from game/data/train.jsonl (#3738)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import aoe2mc  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_production_record import REC  # noqa: E402

AXE = 629174 + 2000         # ms: player 2 researches Double-Bit Axe in its lumber camp 9936 (25 s)


def test_a_lumber_camp_research_is_in_the_production():
    r = replay.Replay(Fake(), data(aoe2mc.read_timeline(REC), n=480))
    assert ("Double-Bit Axe", 629174, 629174 + 25000, "research") in r.production(AXE)[2]


def test_each_book_of_the_menus_has_a_research_time():
    assert replay.RESEARCH_S["Fletching"] == 30 and replay.RESEARCH_S["Feudal Age"] == 130
    r = replay.Replay(Fake(), data(aoe2mc.read_timeline(REC), n=480))
    assert "Double-Bit Axe" not in r.unknown_research and "Fletching" not in r.unknown_research
