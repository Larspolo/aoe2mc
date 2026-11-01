"""#5432: the Graphs, Army, Upgrades, Build order and Spending books and the building line of the live replay are
translate components: each English word comes from a key of game/data/texts.jsonl (names excepted)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_lang_replay_books import keys, texts  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def words(c):
    """The English words of c outside translate keys; a name component (aoe2mc.unit / aoe2mc.tech) is a name."""
    return [w for t in texts(c) for w in t.split() if any(ch.isalpha() for ch in w)]


def replay_keys(c):
    return {k for k in keys(c) if k.startswith("aoe2mc.replay.")}


def test_an_upgrades_page_has_only_translate_texts_for_its_words():
    r = replay.Replay(Fake(), data([]))
    smith = replay.SMITH[0][1][0]
    uni = next(n for n, row in replay.TECH_ROW.items() if row.get("building") == "UNIVERSITY")
    r.upgrades = lambda p, t: {smith, uni} if p == 1 else set()
    assert r.upgrade_view(60_000)
    page = r.books["Upgrades"][1]                                     # the lines of the page of player 1
    assert words(page) == [] and replay_keys(page) <= set(lang.en_us())
    assert {"aoe2mc.replay.university"} <= replay_keys(page)
    assert f"{replay.SMITH[0][0]} 1/{len(replay.SMITH[0][1])}" in [lang.plain(x) for x in page]


def test_the_building_line_has_only_translate_texts_for_its_words():
    r = replay.Replay(Fake(), data([]))
    r.starts, r.placed, r.map = [(None, 1, "HOUSE", (0, 8, 0, 8))], [], None
    r.garrisons = {(0, 8, 0, 8): [1, 2]}
    line = json.loads(r.building_line((4, 2, -4), (0, 0, 1)))
    assert words(line[1:]) == []
    assert replay_keys(line) == {"aoe2mc.replay.building_hp", "aoe2mc.replay.building_garrison"}
    assert "garrison 2" in lang.plain({"text": "", "extra": line}) and "House (" in lang.plain({"text": "", "extra": line})


def test_the_spending_book_has_only_translate_texts_for_its_words():
    r = replay.Replay(Fake(), data([]))
    r.spends = {1: [(0, "military", 100), (0, "economy", 100)]}
    book = json.loads(r.spending_commands(60_000)[0].split("written_book_content=", 1)[1][:-1])
    page = book["pages"][1]
    assert words(page["extra"][1:]) == [] and replay_keys(page) <= set(lang.en_us())
    assert "Military 100 (50 %)" in lang.plain(page) and "Total 200" in lang.plain(page)
