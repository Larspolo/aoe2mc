"""Live replay: the villagers of each player on each kind of work in the sky (#3756). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def game():
    return replay.Replay(Fake(), data([]), ai=True)


def vill(r, name, player, k):
    """A villager of the replay with uuid u<k>, as the timeline makes it."""
    v = gather.Villager(f"u{k}", (0.0, 0.0, 0.0))
    v.name, v.player, v.job = name, player, replay.start_job(name)
    r.units[k] = v
    return v


def rows(cmd):
    """The text components of a summon or data merge command of the economy text."""
    return json.loads(cmd[cmd.index("text:") + 5:].split(",billboard")[0].removesuffix("}"))


def test_the_first_call_summons_one_row_per_player_and_a_repeat_sends_nothing():
    r = game()
    r.grid()
    vill(r, "VILLAGER_MALE", 1, 1)
    vill(r, "VILLAGER_FEMALE", 2, 2)
    first = r.ecoview()
    assert len(first) == 1 and first[0].startswith("summon text_display") and f"Tags:[\"{replay.ECO}\"]" in first[0]
    lines = rows(first[0])
    assert [x["text"] for x in lines] == [f"{r.label(p)[0]}: food 0 · wood 0 · gold 0 · stone 0 · build 0 · idle 1\n"
                                          for p in (1, 2)]
    assert [x["color"] for x in lines] == [r.label(1)[1], r.label(2)[1]]
    assert r.ecoview() == []                                    # the same counts: no command


def test_a_change_of_one_count_sends_one_data_merge():
    r = game()
    r.grid()
    a = vill(r, "VILLAGER_MALE", 1, 1)
    vill(r, "VILLAGER_FEMALE", 2, 2)
    r.ecoview()
    r.look(a, "LUMBERJACK")
    changed = r.ecoview()
    assert len(changed) == 1 and changed[0].startswith(f"data merge entity @e[type=text_display,tag={replay.ECO},limit=1]")
    assert rows(changed[0])[0]["text"] == f"{r.label(1)[0]}: food 0 · wood 1 · gold 0 · stone 0 · build 0 · idle 0\n"
    assert r.ecoview() == []


def test_the_text_of_8_players_stays_below_the_rcon_limit():
    from test_replay_eight_players import eight
    import rcon
    r = replay.Replay(Fake(), eight([]))
    for p in range(1, 9):
        r.pop[p] = 199 - p
        vill(r, "VILLAGER_MALE", p, p)
    (cmd,) = r.ecoview()
    assert len(cmd.encode()) <= rcon.MAX and len(rows(cmd)) == 8
