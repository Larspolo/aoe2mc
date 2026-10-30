"""Live replay: the sidebar line of each player shows its estimated resources (#932). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
import train  # noqa: E402
from test_replay import Fake, build, data  # noqa: E402
from test_replay_gather import TREE, order, play  # noqa: E402
from test_replay_score import play as play_score  # noqa: E402
from test_replay_spawn import queue  # noqa: E402


def lines(sent, p):    # without the APM part (#3764), each line once
    texts = [json.loads(c.split(" ", 6)[6])["text"].split(" · APM")[0] for c in sent
             if c.startswith(f"scoreboard players display name P{p} ")]
    return [t for i, t in enumerate(texts) if i == 0 or t != texts[i - 1]]


def paid(*names):
    """The start resources less the AoE2 costs of the names (train and build COSTS)."""
    import build as builds  # `build` of test_replay is a timeline event
    s = dict(replay.START)
    for n in names:
        for k, v in (train.COSTS.get(n) or builds.COSTS.get(n) or {}).items():
            s[k] -= v
    return s


def est(s):
    """The resources of the sidebar line: never below 0."""
    return " ".join(f"{k[0].upper()} {max(0, v)}" for k, v in s.items())


def test_a_gather_step_raises_the_resource_of_its_player():
    r, sent = play([order(0, 20)], TREE, 60000)
    wood = gather.TREE_WOOD - r.map.trees[(5, 10)]
    s = dict(replay.START, wood=replay.START["wood"] + wood)
    assert wood > 15 and r.stock[1] == s
    r.named.clear()
    assert lines(r.score_commands(), 1) == [f"Player 1 (Britons) · Dark · {est(s)} (est.)"]


def test_a_trained_unit_a_building_and_an_age_cost_their_aoe2_price():
    r = replay.Replay(Fake(), data([]))
    r.pay(2, "VILLAGER_MALE")
    r.commands(build("HOUSE"))
    r.commands(build("HOUSE"))                                         # the same foundation: no second house
    r.age({"player": 1, "age": "FEUDAL_AGE"})
    assert r.stock == {1: paid("HOUSE", "FEUDAL_AGE"), 2: paid("VILLAGER_MALE")}
    r.pop = {1: 1, 2: 1}
    assert lines(r.score_commands(), 1) == [f"Player 1 (Britons) · Feudal · {est(paid('HOUSE', 'FEUDAL_AGE'))} (est.)"]
    assert r.score_commands() == []                                    # no change: no command


def test_the_spawn_of_a_queue_lowers_the_food_in_the_sidebar():
    r, sent = play_score([queue(t=0), dict(time=60_000, player=1, kind="chat", text="gg")])
    assert lines(sent, 1) == [f"Player 1 (Britons) · Dark · {est(replay.START)} (est.)",
                              f"Player 1 (Britons) · Dark · {est(paid('VILLAGER_MALE'))} (est.)"]
