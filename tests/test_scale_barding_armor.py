"""game/train.py: after the research of "Scale Barding Armor" the new cavalry units of the player have it too (#938)."""
from test_forging import setup

from game import combat, train


def test_a_new_scout_has_the_scale_barding_armor():
    server, g = setup()
    g.stock.update(train.COSTS["SCOUT_CAVALRY"])
    g.sites.append({"name": "STABLE", "player": 1, "footprint": [16, 19, 8, 11], "done": True})
    g.techs.add("SCALE_BARDING_ARMOR")
    assert train.queue(g, "Steve", (17, 9), "SCOUT_CAVALRY")
    uuid, = train.tick(g, train.TRAIN_TIMES["SCOUT_CAVALRY"])
    assert combat.stats_command(uuid, "SCOUT_CAVALRY", train.stats(g, "SCOUT_CAVALRY")) in server.log
