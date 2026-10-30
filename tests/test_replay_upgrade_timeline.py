"""Live replay: the Blacksmith tiers of two players in the book "Upgrades", from a timeline through the replay loop (#3784).
Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_stat_books import page  # noqa: E402


def research(player, technology, t):
    return {"time": t, "player": player, "kind": "research", "technology": technology}


def play_to(timeline):
    """Play the timeline through Replay.run (a fake clock) and return the book commands of the last view sent."""
    now, game = [0.0], Fake()
    replay.Replay(game, data(timeline)).run(speed=4, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s),
                                           log=None)
    slot = f"hotbar.{replay.STAT_BOOKS['Upgrades']}"
    cmds = [c for c in game.sent if c.startswith("item ") and slot in c]
    return cmds[max(i for i, c in enumerate(cmds) if c.startswith("item replace")):]


def row(lines, line):
    """The Blacksmith row of one line of a page, for example "Melee 1/3"."""
    return next(x for x in lines if x.startswith(f"{line} "))


def test_two_players_upgrade_rows_at_two_game_times():
    chains = dict(replay.SMITH)
    early = play_to([research(1, "Forging", 1000), research(2, "Fletching", 2000),
                     {"time": 3000, "player": 1, "kind": "chat", "text": "gl"}])
    assert row(page(early, 0), "Melee") == f"Melee 1/{len(chains['Melee'])}"        # player 1
    assert row(page(early, 1), "Archer") == f"Archer 1/{len(chains['Archer'])}"     # player 2
    late = play_to([research(1, "Forging", 1000), research(2, "Fletching", 2000),
                    research(1, "Iron Casting", 4000), {"time": 5000, "player": 1, "kind": "chat", "text": "gl"}])
    assert row(page(late, 0), "Melee") == f"Melee 2/{len(chains['Melee'])}"
