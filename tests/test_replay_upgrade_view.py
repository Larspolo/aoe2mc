"""Live replay: the Blacksmith tiers of each player in the book "Upgrades" (#3786, #3924). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_stat_books import page, pages  # noqa: E402


def tiers(done):
    """The Blacksmith lines of a page with `done` researches of the line of Forging."""
    return [f"{line} {done if 'FORGING' in techs else 0}/{len(techs)}" for line, techs in replay.SMITH]


def test_the_tiers_show_once_and_change_with_a_research():
    r = replay.Replay(Fake(), data([]))
    r.learn({"player": 1, "technology": "Forging", "time": 1000})
    first = r.upgrade_view(2000)
    assert first[0].startswith(f"item replace entity @a hotbar.{replay.STAT_BOOKS['Upgrades']} ")
    assert all(c.startswith("item modify") for c in first[1:])         # longer translate lines (#5432, slot_book)
    assert page(first, 0)[:len(replay.SMITH)] == tiers(1) and page(first, 1)[:len(replay.SMITH)] == tiers(0)
    assert r.upgrade_view(3000) == []                                   # no new research: no command
    r.learn({"player": 1, "technology": "Iron Casting", "time": 4000})
    assert r.upgrade_view(3500) == []                                   # not yet at this game time
    assert page(r.upgrade_view(5000), 0)[:len(replay.SMITH)] == tiers(2)


def test_eight_players_stay_below_the_rcon_limit():
    d = data([])
    d["players"] = {str(p): {"civ": "BYZANTINES", "color": p} for p in range(9)}
    r = replay.Replay(Fake(), d)
    assert r.upgrade_view(0) == []                                      # no research yet: no book
    r.learn({"player": 3, "technology": "Forging", "time": 0})
    cmds = r.upgrade_view(0)
    assert len(pages(cmds)) >= 8 and all(len(c.encode()) <= replay.RCON_MAX for c in cmds)
