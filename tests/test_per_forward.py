"""game/per.py: build-forward builds toward the nearest enemy town center (#4654)."""
import math

from test_bot_gather import bot_map
from test_per_rules import run

from game import per
from game.bot import build

RULE = "(defrule (can-build barracks) => (build-forward barracks))"


def test_build_forward_is_nearer_to_the_enemy_than_home():
    price = build.price(bot_map()[2].g, "BARRACKS")
    s, b, _ = run("(defrule (can-build barracks) => (build-forward barracks) (disable-self))", steps=2, **price)
    (site,) = b.g.sites
    x0, x1, z0, z1 = site["footprint"]
    mid = ((x0 + x1) / 2, (z0 + z1) / 2)
    assert math.dist(mid, (3, 3)) < math.dist(mid, (21, 21))          # the enemy town center is at (3, 3)


def test_build_forward_with_no_enemy_builds_nothing(capsys):
    server, me, b = bot_map()
    b.g.stock.update(build.price(b.g, "BARRACKS"))
    b.g.data["objects"] = [o for o in b.g.data["objects"] if o["kind"] != "building" or o["player"] != 1]
    s = per.Script(per.parse(RULE), b)
    s.step()
    s.step()
    assert b.g.sites == [] and capsys.readouterr().err == ""
