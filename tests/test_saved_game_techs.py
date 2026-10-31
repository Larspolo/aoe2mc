"""#4623 (epic #4561): read_saved gives each player of a saved game its researched technologies ("techs"), from the
tech table of the save; a player with "techs" gets only the age technologies of its age (scenario.start_values)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import build  # noqa: E402
import scenario  # noqa: E402
import train  # noqa: E402
from test_scenario_mode import game  # noqa: E402

import aoe2mc  # noqa: E402

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


def techs(name):
    return {n: p.get("techs") for n, p in aoe2mc.read_saved(os.path.join(SAMPLES, name))[6].items() if n}


def test_read_saved_gives_the_researched_technologies_of_each_player():
    # the owner researched Loom, the Feudal Age and Double-Bit Axe; the AI researched Loom (#4623)
    assert techs("aoe2mc-sample-feudal.aoe2spgame") == {1: ["LOOM", "FEUDAL_AGE", "DOUBLE_BIT_AXE"], 2: ["LOOM"]}


def test_two_saves_of_one_game_differ_by_the_one_new_technology():
    assert techs("aoe2mc-tech-a.aoe2spgame") == {1: [], 2: []}
    assert techs("aoe2mc-tech-b.aoe2spgame") == {1: ["LOOM"], 2: []}


def test_save_techs_skips_a_free_technology_and_counts_a_record_with_no_anchor():
    anchor = bytes.fromhex("600a0000600a0000600a")

    def record(time, state, size=80):
        return (aoe2mc.struct.pack("<fh", time, state) + bytes(9) + anchor).ljust(size, b"\0")
    data = record(0, 3) + record(25.0, 3, 170) + record(9.0, 3) + record(9.0, 1)
    assert aoe2mc.save_techs(data) == [1, 3]   # 0: free; after the long 1 the record 2 has no anchor; 4: not done


def test_a_player_with_techs_gets_only_the_age_technologies():
    dark = next(t for t in train.TECHS if train.value("age", t, 0) == 0 and t not in build.AGE_TECHS
                and t not in train.ONE_BUILDING)
    _, g, bot = game({"0": {}, "1": {"age": "feudal", "techs": [], "saved": True},
                      "2": {"age": "feudal", "saved": True}})
    for x in (g, bot):
        scenario.start_values(x, g.players[str(x.player)])
    assert build.ages(g) == 1 and build.ages(bot) == 1
    assert dark not in g.techs and dark in bot.techs
