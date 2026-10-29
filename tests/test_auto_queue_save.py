"""A saved game keeps the auto-queue of each building (#3525, #3522): after a load the building trains its auto-queue
unit again when its queue is empty."""
import json

from test_auto_queue import RECT, right, run
from test_train_barracks import setup

from game import savegame, train


def test_a_load_keeps_the_auto_queue_and_trains_again():
    server, g = setup(food=500, gold=500)
    train.open_menu(g, "Steve", (11, 3))
    right(g)
    text = json.dumps(savegame.dump(g), sort_keys=True)
    hserver, h = setup(food=500, gold=500)
    savegame.load(h, json.loads(text))
    assert h.auto == g.auto == {RECT: "MILITIA"} and all(isinstance(k, tuple) for k in h.auto)
    assert len(run(h, hserver, 30)) == 1
