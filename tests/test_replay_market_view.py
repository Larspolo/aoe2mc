"""Live replay: a market trade shows its text above the market for its time (#3942). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_market import trade  # noqa: E402
from test_replay_research import play, texts  # noqa: E402

MARKET = {"kind": "building", "name": "MARKET", "player": 1, "ref": 12239, "tile": [8.0, 8.0],
          "footprint": [26, 26, 38, 38]}


def replay_():
    d = data([])
    d["objects"].append(MARKET)
    return replay.Replay(Fake(), d)


def test_a_buy_shows_the_wood_and_the_gold_above_the_market():
    cmds = replay_().commands(trade("buy", 100))
    (summon,) = texts(cmds)
    x, y, z = map(float, summon.split()[2:5])
    assert (x, z) == (32.0, 32.0)
    assert "+100 wood \\u2212130 gold" in summon
    assert any(c.startswith("particle ") for c in cmds)


def test_two_trades_in_one_second_give_one_text_with_the_sum():
    r = replay_()
    first = r.commands(trade("sell", 100, "Food", t=1000))
    second = r.commands(trade("sell", 100, "Food", t=2000))
    assert len(texts(first)) == 1 and not texts(second)
    (merge,) = second
    assert merge.startswith("data merge entity @e[type=text_display") and "+200 food" not in merge
    assert "\\u2212200 food +160 gold" in merge


def test_the_text_goes_after_its_time():
    sent = play([trade("buy", 100), {"time": 30000, "player": 1, "kind": "chat", "text": "x"}], [MARKET])
    (summon,) = texts(sent)
    tag = summon.split('Tags:["aoe2mc.effect","')[1].split('"')[0]
    chat = next(k for k, c in enumerate(sent) if c.startswith("tellraw"))
    assert sent.index(summon) < sent.index(f"kill @e[type=text_display,tag={tag}]") < chat
