"""Live replay: the sidebar line of each player shows its estimated resources (#932). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, build, data  # noqa: E402
from test_replay_gather import TREE, order, play  # noqa: E402
from test_replay_score import play as play_score  # noqa: E402
from test_replay_spawn import queue  # noqa: E402


def lines(sent, p):    # without the APM part (#3764), each line once
    texts = [json.loads(c.split(" ", 6)[6])["text"].split(" · APM")[0] for c in sent
             if c.startswith(f"scoreboard players display name P{p} ")]
    return [t for i, t in enumerate(texts) if i == 0 or t != texts[i - 1]]


def test_a_gather_step_raises_the_resource_of_its_player():
    r, sent = play([order(0, 20)], TREE, 60000)
    wood = 100 - r.map.trees[(5, 10)]
    assert wood > 15 and r.stock[1] == {"food": 200, "wood": 200 + wood, "gold": 100, "stone": 200}
    r.named.clear()
    assert lines(r.score_commands(), 1) == [f"Player 1 (Britons) · Dark · F 200 W {200 + wood} G 100 S 200 (est.)"]


def test_a_trained_unit_a_building_and_an_age_cost_their_aoe2_price():
    r = replay.Replay(Fake(), data([]))
    r.pay(2, "VILLAGER_MALE")
    r.commands(build("HOUSE"))
    r.commands(build("HOUSE"))                                         # the same foundation: no second house
    r.age({"player": 1, "age": "FEUDAL_AGE"})
    assert r.stock == {1: {"food": -300, "wood": 175, "gold": 100, "stone": 200},
                       2: {"food": 150, "wood": 200, "gold": 100, "stone": 200}}
    r.pop = {1: 1, 2: 1}
    assert lines(r.score_commands(), 1) == ["Player 1 (Britons) · Feudal · F 0 W 175 G 100 S 200 (est.)"]   # never < 0
    assert r.score_commands() == []                                    # no change: no command


def test_the_spawn_of_a_queue_lowers_the_food_in_the_sidebar():
    r, sent = play_score([queue(t=0), dict(time=60_000, player=1, kind="chat", text="gg")])
    assert lines(sent, 1) == ["Player 1 (Britons) · Dark · F 200 W 200 G 100 S 200 (est.)",
                              "Player 1 (Britons) · Dark · F 150 W 200 G 100 S 200 (est.)"]
