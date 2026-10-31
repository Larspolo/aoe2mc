"""Live replay: the end of a replay names the relics of each player in the Society line, and the timeline book shows
the arrival of each relic in a monastery (#4035, item 6 of #4008). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_relic_monastery import CHURCH, OTHER, home  # noqa: E402
from test_replay_relic_pickup import MONK, RELIC  # noqa: E402
from test_replay_society import lines  # noqa: E402

RELIC2 = dict(RELIC, ref=31, tile=[5.5, 11.5])
BOOK = "give @a minecraft:written_book[minecraft:written_book_content="


def order(t, i, target):
    return dict(time=t, player=1, kind="order", objects=[i], target=target, names=["MONK"])


def two_relics():
    """Monk 7 carries relic 30 home at 15 s and relic 31 home at 55 s; the replay ends at 120 s."""
    timeline = [{"time": 10_000, "player": 1, "kind": "age", "age": "FEUDAL_AGE"},
                order(0, 7, 30), home(15_000, 40), order(40_000, 7, 31), home(55_000, 40),
                {"time": 120_000, "player": 1, "kind": "chat", "text": "end"}]
    d = data(timeline)
    player2 = {"kind": "unit", "name": "VILLAGER_MALE", "player": 2, "uuid": "v2", "ref": 12, "tile": [2.5, 20.5]}
    d["objects"] += [MONK, RELIC, RELIC2, CHURCH, OTHER, player2]     # player 2 has a villager: a Society line
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d)
    r.run(speed=8, clock=lambda: now[0], sleep=sleep, log=None, bar=True)
    return r, game.sent


def page_text(page):
    return lang.plain(page) + "".join(page_text(e) for e in page.get("extra", []))


def timeline_rows(sent):
    cmd = next(c for c in sent if c.startswith(BOOK) and '"title":"Timeline"' in c)
    book = json.loads(cmd[len(BOOK):-1])
    return [row for page in book["pages"] for row in page_text(page).split("\n") if "Relic" in row or "Feudal" in row]


def test_the_society_line_counts_the_relics_of_each_player():
    r, sent = two_relics()
    got = lines(sent)
    assert r.relic_count(1) == 2 and r.relic_count(2) == 0
    assert any(x.startswith("Player 1") and "wonders 0, relics 2," in x for x in got)
    assert any(x.startswith("Player 2") and "wonders 0, relics 0," in x for x in got)


def test_the_timeline_book_has_a_line_per_relic_in_time_order():
    r, sent = two_relics()
    assert r.relics[30]["home_t"] < r.relics[31]["home_t"]
    assert timeline_rows(sent) == ["00:10 Feudal Age", "00:18 Relic", "00:56 Relic"]
