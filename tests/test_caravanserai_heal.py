"""game/trade.py: an own complete Caravanserai heals the trade carts of its player and its allies in its aura (a square
some tiles from each edge) by its hit points per AoE2 second (trade.HEALS), up to their max (#2353, AoE2 DE wiki
"Caravanserai (Age of Empires II)"). Fake server."""
import pytest
from test_gather import grid
from test_monk_heal import HealServer

from game import gather, trade

SERAI = [10, 10, 14, 14]                                               # x0, z0, x1, z1 (tile size 1)
RATE = trade.HEALS["CARAVANSERAI"][0]                                  # hit points per AoE2 second


def setup(serai=True, site=None):
    """A flat 40 × 40 map: an own Caravanserai, an injured cart "near" in its aura, one "far" out of it and a full one."""
    objects = [{"kind": "unit", "name": "TRADE_CART_EMPTY", "player": 1, "uuid": u, "tile": [x, 12.5]}
               for u, x in (("near", 20.5), ("far", 22.5), ("full", 4.5))]
    objects += [{"kind": "building", "name": "CARAVANSERAI", "player": 1, "footprint": SERAI}] * serai
    server = HealServer({"near": {"Pos": (20.5, 64.0, 12.5), "Health": 40.0, "Max": 70.0},   # 7 tiles from the edge
                         "far": {"Pos": (22.5, 64.0, 12.5), "Health": 40.0, "Max": 70.0},
                         "full": {"Pos": (4.5, 64.0, 12.5), "Health": 70.0, "Max": 70.0}})
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    if site:
        g.sites.append(site)
    return server, g


def run(g, seconds):
    for _ in range(int(seconds)):
        trade.heal(g, 1.0)


def test_a_cart_in_the_aura_gets_its_hit_points_per_second_up_to_its_max():
    server, g = setup()
    run(g, 10)
    assert server.entities["near"]["Health"] == pytest.approx(min(70.0, 40.0 + 10 * RATE))
    assert server.entities["far"]["Health"] == 40.0                    # 9 tiles from the edge: out of the aura
    assert not any("full Health set" in c for c in server.log)         # a full cart gets no command
    run(g, 60)
    assert server.entities["near"]["Health"] == 70.0


def test_no_heal_without_a_complete_caravanserai():
    server, g = setup(serai=False, site={"name": "CARAVANSERAI", "player": 1, "footprint": [10, 14, 10, 14]})   # x0, x1, z0, z1
    run(g, 10)
    assert server.entities["near"]["Health"] == 40.0
    g.sites[0]["done"] = True                                          # a built Caravanserai heals
    run(g, 10)
    assert server.entities["near"]["Health"] == pytest.approx(min(70.0, 40.0 + 10 * RATE))
