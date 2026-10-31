"""#5390: the Timeline book and the military summary line of the live replay are translate components: each English
word comes from a key of game/data/texts.jsonl (or a unit or technology name), and a long book goes into more commands."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_army_summary import military_lines  # noqa: E402

PREFIX = "give @a minecraft:written_book[minecraft:written_book_content="


def texts(c):
    """The literal texts of component c (not the fallbacks of its translate keys)."""
    if isinstance(c, str):
        return [c]
    if not isinstance(c, dict):
        return [t for x in c for t in texts(x)]
    out = [] if "translate" in c else [c.get("text", "")]
    return out + [t for x in c.get("with", []) + c.get("extra", []) for t in texts(x)]


def keys(c):
    if not isinstance(c, dict):
        return [k for x in c for k in keys(x)] if isinstance(c, list) else []
    return [c.get("translate")] * ("translate" in c) + [k for x in c.get("with", []) + c.get("extra", []) for k in keys(x)]


EVENTS = [{"time": 60_000, "player": 1, "kind": "age", "age": "FEUDAL_AGE"},
          {"time": 90_000, "player": 1, "kind": "resign"}]


def test_a_timeline_page_has_only_translate_texts_for_its_words():
    cmd, = replay.Replay(Fake(), data(EVENTS)).timeline_commands(10**9)
    page = json.loads(cmd[len(PREFIX):-1])["pages"][1]
    words = [w for t in texts(page["extra"][1:]) for w in t.split() if any(ch.isalpha() for ch in w)]
    assert words == [] and {"aoe2mc.tech.FEUDAL_AGE", "aoe2mc.replay.tl_resigns"} <= set(keys(page))
    assert "01:00 Feudal Age" in lang.plain(page) and "01:30 Resigns" in lang.plain(page)


def test_the_military_summary_line_has_only_translate_texts_for_its_words():
    r = replay.Replay(Fake(), data([]))
    r.army, r.troops, r.fallen = {1: 2}, {1: {"KNIGHT": 2}}, {1: {"ARCHER": 1}}
    line, = [json.loads(c.split(" ", 2)[2]) for c in r.summary_commands() if "aoe2mc.replay.sum_military" in c]
    army = line[1]["with"][-1]
    assert {"aoe2mc.replay.army_end", "aoe2mc.replay.army_lost"} <= set(keys(army))
    assert not [t for t in texts(army) if any(ch.isalpha() for ch in t) and t not in ("2 Knight", "1 Archer")]
    assert military_lines(r)[0].endswith("army at the end: 2 Knight, lost: 1 Archer")


def test_a_long_book_goes_into_more_commands_and_keeps_all_lines():
    many = [{"time": 1000 * i, "player": 1 + i % 8, "kind": "age", "age": "IMPERIAL_AGE"} for i in range(400)]
    cmds = replay.Replay(Fake(), data(many)).timeline_commands(10**9)
    assert len(cmds) > 1 and all(len(c.encode()) <= replay.RCON_MAX for c in cmds)
    assert cmds[0].startswith("item replace entity @a inventory.0 with minecraft:written_book")
    assert all(c.startswith("item modify entity @a inventory.0 ") for c in cmds[1:])
    assert sum(c.count("aoe2mc.tech.IMPERIAL_AGE") for c in cmds) == 400
