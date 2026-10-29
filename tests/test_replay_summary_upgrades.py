"""Live replay: the Blacksmith researches and the counts of economy and University researches in the summary (#3789).
Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_learned import research  # noqa: E402


def lines(r):
    """The text of the upgrade lines of the summary, one per player."""
    out = [json.loads(c.split(" ", 2)[2]) for c in r.tech_commands()]
    return ["".join(t["text"] for t in parts) for parts in out if "economy" in parts[-1]["text"]]


def test_the_blacksmith_researches_and_the_economy_count_are_one_line():
    r = replay.Replay(Fake(), data([]))
    r.learn(research(480_000, "Forging"))
    r.learn(research(732_000, "Iron Casting"))
    r.learn(research(545_000, "Fletching"))
    r.learn(research(300_000, "Double-Bit Axe"))
    r.learn(research(400_000, "Two-Man Saw"))
    assert lines(r) == ["Player 1 (Britons): Forging 8:00, Iron Casting 12:12, Fletching 9:05 · economy 2 · University 0"]


def test_a_player_with_no_research_gets_no_upgrade_line():
    r = replay.Replay(Fake(), data([]))
    r.learn(research(300_000, "Masonry", player=2))
    r.learn(research(1000, "Loom", player=1))                       # a Town Center research: no upgrade line
    assert lines(r) == ["Player 2 (Aztecs): economy 0 · University 1"]


def test_more_than_12_blacksmith_researches_end_with_plus_n():
    r = replay.Replay(Fake(), data([]))
    for i, tech in enumerate(["Forging", "Scale Mail Armor", "Fletching", "Padded Archer Armor", "Scale Barding Armor",
                              "Chain Mail Armor", "Leather Archer Armor", "Chain Barding Armor", "Iron Casting",
                              "Bodkin Arrow", "Blast Furnace", "Plate Mail Armor", "Ring Archer Armor"]):
        r.learn(research(1000 * (i + 1), tech))
    text = lines(r)[0]
    assert text.count(",") == 12 and text.endswith(", +1 · economy 0 · University 0")
