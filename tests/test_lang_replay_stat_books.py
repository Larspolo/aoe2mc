"""#5421: the Economy book and the summary lines of society, upgrades and the task word of the live replay are
translate components: each English word comes from a key of game/data/texts.jsonl."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_lang_replay_books import keys, texts  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def words(c):
    return [w for t in texts(c) for w in t.split() if any(ch.isalpha() for ch in w)]


def known(c):
    return set(keys(c)) <= set(lang.en_us())


def test_an_economy_page_has_only_translate_texts_for_its_words():
    r = replay.Replay(Fake(), data([]))
    r.eco = lambda: {1: {"food": 3, "wood": 2}}
    cmd = r.ecoview()[0]
    page = json.loads(cmd.split(',"pages":[', 1)[1].rsplit("]}]", 1)[0].split(',{"text":"","extra"', 1)[0])
    body = page["extra"][1:]
    assert words(body) == [] and known(page)
    assert {"aoe2mc.replay.eco_food", "aoe2mc.replay.spent", "aoe2mc.replay.spent_military"} <= set(keys(page))
    assert "food 3" in lang.plain(page) and "Spent:" in lang.plain(page)


def test_the_society_line_has_only_translate_texts_for_its_words():
    r = replay.Replay(Fake(), data([]))
    r.pop = {1: 3}
    line, = [json.loads(c.split(" ", 2)[2]) for c in r.society_commands()]
    assert words(line[1:]) == [] and known(line)
    assert {"aoe2mc.replay.soc_relics", "aoe2mc.replay.soc_market"} <= set(keys(line))
    assert "relics 0, bought 0, sold 0, tribute sent 0" in lang.plain({"text": "", "extra": line[1:]})


def test_the_task_word_is_a_translate_text():
    r = replay.Replay(Fake(), data([]))
    assert keys(r.task(12345)) == ["aoe2mc.replay.task_idle"] and lang.plain(r.task(12345)) == "idle"
