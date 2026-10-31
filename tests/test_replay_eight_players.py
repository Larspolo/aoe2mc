"""Live replay with 8 players (#1191): each player has its own color in the chat, the sidebar and the fireworks,
and --follow N works for each N. No sample record has 8 players: a synthetic aoe2mc.json. Fake RCON."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_walk import VIL  # noqa: E402

import buildings  # noqa: E402

CIVS = ["BRITONS", "FRANKS", "GOTHS", "TEUTONS", "JAPANESE", "CHINESE", "BYZANTINES", "PERSIANS"]
PLAYERS = range(1, 9)


def eight(timeline):
    """A 32 × 32 tile map: 8 players in the AoE2 colors, a town center and a villager for each."""
    d = data(timeline, n=128)
    d["players"] = {str(p): {"civ": CIVS[p - 1], "color": buildings.COLOR_NAMES[p - 1], "arch": "western"}
                    for p in PLAYERS}
    for p in PLAYERS:
        x, z = 16 * ((p - 1) % 4), 64 * ((p - 1) // 4)              # 4 town centers in a row, 2 rows
        d["objects"] += [{"kind": "building", "name": "TOWN_CENTER", "player": p, "ref": 100 + p,
                          "tile": [x / 4 + 2, z / 4 + 2], "footprint": [x, z, x + 16, z + 16]},
                         dict(VIL, player=p, uuid=f"u{p}", ref=p, tile=[x / 4 + 2.5, z / 4 + 6.5])]
    return d


def play(timeline, follow=None):
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, eight(timeline), follow=follow)
    r.run(clock=lambda: now[0], sleep=sleep, log=None, bar=True, finish=True)
    return r, game.sent


def tellraws(sent):
    return [json.loads(c[len("tellraw @a "):]) for c in sent if c.startswith("tellraw @a [")]


def test_each_player_has_its_own_text_color_in_the_chat():
    r = replay.Replay(Fake(), eight([]))
    colors = [json.loads(r.commands({"time": 0, "player": p, "kind": "chat", "text": "gl"})[0][11:])[0]["color"]
              for p in PLAYERS]
    assert colors == ["blue", "red", "green", "yellow", "aqua", "light_purple", "dark_gray", "gold"]


def test_each_player_has_its_own_firework_color_above_its_own_town_center():
    r = replay.Replay(Fake(), eight([]))
    seen = []
    for p in PLAYERS:
        fw = [c for c in r.commands({"time": 1, "player": p, "kind": "age", "age": "FEUDAL_AGE"})
              if c.startswith("summon minecraft:firework_rocket ")]
        assert len(fw) == 3
        x, _, z = map(float, fw[0].split()[2:5])
        assert (x, z) == (16 * ((p - 1) % 4) + 8, 64 * ((p - 1) // 4) + 8)
        seen.append(re.search(r'"colors": \[I; (\d+)\]', fw[0])[1])
    assert len(set(seen)) == 8


def test_the_sidebar_has_8_lines_in_8_colors():
    _, sent = play([dict(time=1000, player=8, kind="chat", text="gg")])
    sets = [c.split()[3] for c in sent if c.startswith("scoreboard players set ") and replay.POP in c]
    assert sets == [f"P{p}" for p in PLAYERS]
    names = [json.loads(c.split(" ", 6)[6]) for c in sent if c.startswith("scoreboard players display name ")]
    first = {}                                   # the APM (#3764) renames a player again: the first name of each
    for n in names:
        first.setdefault(lang.plain(n).split(" · ")[0], n)
    names = list(first.values())
    assert [lang.plain(n).split(" · ")[0] for n in names] == [f"Player {p} ({c.title()})" for p, c in zip(PLAYERS, CIVS)]
    assert len({n["color"] for n in names}) == 8


def test_the_summary_has_the_lines_of_each_player():
    _, sent = play([dict(time=1000, player=p, kind="age", age="FEUDAL_AGE") for p in PLAYERS])
    lines = [t for t in tellraws(sent) if isinstance(t, list) and lang.plain(t[0]).startswith("Player ")
             and lang.plain(t[1]).startswith((": villagers", ": military", ": Feudal", ": castles"))]
    for p in PLAYERS:
        mine = [t for t in lines if lang.plain(t[0]).startswith(f"Player {p} ")]
        assert len(mine) == 4                                 # economy, military, ages, society
        assert {t[0]["color"] for t in mine} == {replay.TEXT_COLORS[buildings.COLOR_NAMES[p - 1]]}


def test_follow_works_for_each_player():
    tl = [dict(time=100 * p, player=p, kind="move", objects=[p], tile=[16.5, 16.5]) for p in PLAYERS]
    for p in PLAYERS:
        _, sent = play(tl, follow=p)
        assert [c.split()[1] for c in sent if c.endswith(f" add {replay.FOLLOWED}") and c.startswith("tag u")] == [f"u{p}"]
