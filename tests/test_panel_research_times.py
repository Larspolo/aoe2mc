"""The production panel of the live replay shows each research of the record, also outside the town center: the
research seconds come from game/data/train.jsonl (#3738)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_production_record import REC  # noqa: E402

import aoe2mc  # noqa: E402

AXE = 629174 + 2000         # ms: player 2 researches Double-Bit Axe in its lumber camp 9936


def test_a_lumber_camp_research_is_in_the_production():
    r = replay.Replay(Fake(), data(aoe2mc.read_timeline(REC), n=480))
    end = 629174 + round(replay.RESEARCH_S["Double-Bit Axe"] * 1000)
    assert ("Double-Bit Axe", 629174, end, "research") in r.production(AXE)[2]


def test_each_book_of_the_menus_has_a_research_time():
    assert all(s > 0 for s in replay.RESEARCH_S.values())
    r = replay.Replay(Fake(), data(aoe2mc.read_timeline(REC), n=480))
    assert "Double-Bit Axe" not in r.unknown_research and "Fletching" not in r.unknown_research
