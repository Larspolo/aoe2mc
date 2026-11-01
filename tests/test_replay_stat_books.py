"""Live replay: the stats of the spectators are written books in the hotbar, no text in the sky at the center of the
map (#3924). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def pages(cmds):
    """The plain text of each page of the book that the commands put into a hotbar slot (item replace, item modify)."""
    out = []
    for c in cmds:
        inner = c.split('"pages":[', 1)[1][:-3] if c.startswith("item replace") else c.split("pages:[", 1)[1][:-2]
        out += [lang.plain(pg) for pg in json.loads(f"[{inner}]")]          # also translate lines (#5421)
    return out


def page(cmds, k=0):
    """The lines of page k with no heading (the first page of a player starts with its name and an empty line)."""
    lines = pages(cmds)[k].split("\n")
    return lines[2:] if lines[0].startswith("■") else lines


def test_a_book_goes_into_its_hotbar_slot_and_only_when_its_lines_change():
    r = replay.Replay(Fake(), data([]))
    cmds = r.stat_book("Economy", {1: ["food 2"], 2: ["wood 1"]})
    assert len(cmds) == 1 and cmds[0].startswith(f"item replace entity @a hotbar.{replay.STAT_BOOKS['Economy']} with "
                                                  "minecraft:written_book[")
    assert page(cmds, 0) == ["food 2"] and page(cmds, 1) == ["wood 1"]
    assert r.stat_book("Economy", {1: ["food 2"], 2: ["wood 1"]}) == []
    assert page(r.stat_book("Economy", {1: ["food 3"], 2: ["wood 1"]})) == ["food 3"]


def test_the_hotbar_slots_of_the_books_are_free():
    import replay_input
    used = {slot for slot, _, _ in replay_input.ITEMS.values()}
    slots = list(replay.STAT_BOOKS.values())
    assert len(set(slots)) == len(slots) and not used & set(slots) and all(0 <= s <= 8 for s in slots)


def test_a_long_book_of_8_players_appends_its_pages_below_the_rcon_limit():
    from test_replay_eight_players import eight
    r = replay.Replay(Fake(), eight([]))
    lines = {p: [f"Pop {'█' * replay.GRAPH_MINUTES} {99999 - p}"] * 4 for p in range(1, 9)}
    cmds = r.stat_book("Graphs", lines)
    assert len(cmds) > 1 and all(c.startswith("item modify entity @a hotbar.3 ") for c in cmds[1:])
    assert 'type:"minecraft:set_written_book_pages",mode:"append"' in cmds[1]
    assert max(len(c.encode()) for c in cmds) <= replay.RCON_MAX
    assert len(pages(cmds)) == 8 and all(page(cmds, k) == lines[k + 1] for k in range(8))


def test_a_replay_summons_no_text_in_the_sky_and_gives_the_books():
    from test_replay_control import Clock
    d = data([{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
              {"time": 70000, "player": 1, "kind": "chat", "text": "end"}])
    game = Clock()
    r = replay.Replay(game, d)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None)
    center = f"{r.n / 2:.1f}"
    assert not [c for c in game.sent if c.startswith(f"summon text_display {center} ")]
    assert any(c.startswith("item replace entity @a hotbar.3 ") for c in game.sent)       # the graphs
