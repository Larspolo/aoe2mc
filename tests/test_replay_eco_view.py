"""Live replay: the villagers of each player on each kind of work in the book "Economy" (#3756, #3924). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_stat_books import page, pages  # noqa: E402


def game():
    return replay.Replay(Fake(), data([]), ai=True)


def vill(r, name, player, k):
    """A villager of the replay with uuid u<k>, as the timeline makes it."""
    v = gather.Villager(f"u{k}", (0.0, 0.0, 0.0))
    v.name, v.player, v.job = name, player, replay.start_job(name)
    r.units[k] = v
    return v


def test_the_first_call_gives_a_page_per_player_and_a_repeat_sends_nothing():
    r = game()
    r.grid()
    vill(r, "VILLAGER_MALE", 1, 1)
    vill(r, "VILLAGER_FEMALE", 2, 2)
    first = r.ecoview()
    assert len(first) == 1 and first[0].startswith(f"item replace entity @a hotbar.{replay.STAT_BOOKS['Economy']} ")
    assert [page(first, k) for k in (0, 1)] == [["food 0", "wood 0", "gold 0", "stone 0", "build 0", "idle 1"]] * 2
    assert r.ecoview() == []                                    # the same counts: no command


def test_a_change_of_one_count_changes_the_book():
    r = game()
    r.grid()
    a = vill(r, "VILLAGER_MALE", 1, 1)
    vill(r, "VILLAGER_FEMALE", 2, 2)
    r.ecoview()
    r.look(a, "LUMBERJACK")
    changed = r.ecoview()
    assert len(changed) == 1 and page(changed, 0) == ["food 0", "wood 1", "gold 0", "stone 0", "build 0", "idle 0"]
    assert r.ecoview() == []


def test_the_book_of_8_players_stays_below_the_rcon_limit():
    from test_replay_eight_players import eight
    import rcon
    r = replay.Replay(Fake(), eight([]))
    for p in range(1, 9):
        r.pop[p] = 199 - p
        vill(r, "VILLAGER_MALE", p, p)
    cmds = r.ecoview()
    assert max(len(c.encode()) for c in cmds) <= rcon.MAX and len(pages(cmds)) == 8
