"""Live replay: a research shows its name and particles above its building for 10 game seconds (#843). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, build, data  # noqa: E402

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 5, "tile": [8.0, 8.0], "footprint": [26, 26, 38, 38]}


def research(t, i, name, tech="Loom"):
    return {"time": t, "player": 1, "kind": "research", "objects": [i], "names": [name], "technology": tech}


def play(timeline, objects=(), jump=None):
    """Play the timeline and return the sent commands. jump = (game time a, game time b), ms: at a, jump to b."""
    d = data(timeline)
    d["objects"] += list(objects)
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    todo = [jump] if jump else []

    def poll(c):
        if todo and c["time"] >= todo[0][0]:
            c["jump"] = todo.pop()[1]
    replay.Replay(game, d).run(clock=lambda: now[0], sleep=sleep, log=None, poll=poll)
    return game.sent


def texts(sent):
    return [c for c in sent if c.startswith("summon text_display") and replay.EFFECT in c]    # not the panel (#2811)


def test_a_research_of_a_start_building_shows_its_name_above_the_roof():
    d = data([])
    d["objects"].append(TC)
    r = replay.Replay(Fake(), d)
    cmds = r.commands(research(1000, 5, "TOWN_CENTER"))
    assert cmds[0].startswith("title @a actionbar ")
    (summon,) = texts(cmds)
    x, y, z = map(float, summon.split()[2:5])
    assert (x, z) == (32.0, 32.0) and y > 70 + 10                    # above the roof of the town center
    assert '"text": "Loom", "color": "blue"' in summon and 'billboard:"center"' in summon
    assert any(c.startswith("particle minecraft:enchant") for c in cmds)


def test_the_text_goes_after_10_game_seconds():
    sent = play([research(1000, 5, "TOWN_CENTER"), {"time": 30000, "player": 1, "kind": "chat", "text": "x"}],
                [TC])
    (summon,) = texts(sent)
    tag = summon.split('Tags:["aoe2mc.effect","')[1].split('"')[0]
    kill = sent.index(f"kill @e[type=text_display,tag={tag}]")
    chat = next(k for k, c in enumerate(sent) if c.startswith("tellraw"))
    assert sent.index(summon) < kill < chat                          # at 11 s, before the chat line at 30 s


def test_a_research_of_a_replay_building_uses_its_top():
    house = build("HOUSE", (8.0, 8.0), 1000)
    r = replay.Replay(Fake(), data([house]))
    r.commands(house)
    rect = r.placed[-1][2]
    (summon,) = texts(r.commands(research(2000, 900, "HOUSE", "Wheelbarrow")))
    assert float(summon.split()[3]) == r.tops[rect] + 3
    assert r.ids[900] == rect


def test_an_unknown_building_gives_only_the_action_bar_line():
    r = replay.Replay(Fake(), data([]))
    assert len(r.commands(research(1000, 900, "BLACKSMITH"))) == 1
    assert len(r.commands({"time": 1, "player": 1, "kind": "research", "technology": "Loom"})) == 1


def test_a_jump_skips_the_text_and_removes_an_old_one():
    sent = play([research(1000, 5, "TOWN_CENTER"), {"time": 60000, "player": 1, "kind": "chat", "text": "x"}],
                [TC], (0, 30000))
    assert texts(sent) == []                                         # the skipped time shows no text
    sent = play([research(1000, 5, "TOWN_CENTER"), {"time": 60000, "player": 1, "kind": "chat", "text": "x"}],
                [TC], (2000, 30000))
    kills = [k for k, c in enumerate(sent) if c.startswith(f"kill @e[type=text_display,tag={replay.EFFECT}")]
    assert len(texts(sent)) == len(kills) == 1
    assert kills[0] < next(k for k, c in enumerate(sent) if c.startswith("tellraw"))   # at the jump, not at the end
