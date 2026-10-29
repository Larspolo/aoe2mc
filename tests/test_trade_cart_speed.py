"""A trade cart (a donkey: a wide mob that the plugin steers) walks at its AoE2 speed in both directions (#1344). It
walked 27 % faster to the north-west: the path follow passed the next point after steer(), and the input pushed on."""
import math

import pytest

from game import gather


@pytest.mark.mc
def test_a_trade_cart_walks_a_diagonal_at_its_aoe2_speed_both_ways(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import time

    import aoe2mc
    import scenarios

    from game import ai, run, train
    src = str(tmp_path / "t.aoe2scenario")
    scenarios.save(scenarios.new_scenario(48), src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    a, b = (30, 30), (110, 110)                                         # 113 blocks
    need = ai.walk_speed("TRADE_CART", 4)                              # blocks per second at Normal speed
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        cart = train.summon(g, "TRADE_CART", (a[0] + 0.5, float(g.map.y(*a)), a[1] + 0.5))
        speeds = []
        for frm, (x, z) in ((a, b), (b, a)):                           # to the south-east, then to the north-west
            assert "Moved 1" in ai.move(game, cart, "TRADE_CART", g.map.T, x + 0.5, g.map.y(x, z), z + 0.5)
            samples, end = [], time.monotonic() + 30
            while time.monotonic() < end and not (samples and math.dist(samples[-1][1], (x + 0.5, z + 0.5)) < 2):
                if p := g.pos(cart):
                    samples.append((time.monotonic(), p[::2]))
                time.sleep(0.25)
            mid = [(t, p) for t, p in samples if math.dist(p, (frm[0] + 0.5, frm[1] + 0.5)) > 15
                   and math.dist(p, (x + 0.5, z + 0.5)) > 15]                # no start and no stop
            (t1, p1), (t2, p2) = mid[0], mid[-1]
            speeds.append(math.dist(p1, p2) / (t2 - t1))
        assert all(abs(s - need) <= 0.5 for s in speeds), (speeds, need)
