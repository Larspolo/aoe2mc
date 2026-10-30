"""A wide mob (a trade cart: a donkey that the plugin steers) keeps its long path on a flat field (#1359). Its path
index stopped behind it when it ate grass (no AI step for 50 ticks, but steer() moved it on): the cart walked on to
the end of its partial path, and the plugin dropped the order ("no path")."""
import math

import pytest

from game import gather


@pytest.mark.mc
def test_five_trade_cart_trips_to_the_south_east_arrive_in_time(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import time

    import scenarios

    import aoe2mc
    from game import ai, run, train
    src = str(tmp_path / "t.aoe2scenario")
    scenarios.save(scenarios.new_scenario(48), src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    a, b = (20, 20), (150, 150)                                         # 184 blocks: more than the path reach
    most = 1.3 * math.dist(a, b) / (1.25 * 4 * gather.NORMAL)          # AoE2: 1.25 tiles per second
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        times = []
        for trip in range(5):
            cart = train.summon(g, "TRADE_CART", (a[0] + 0.5, float(g.map.y(*a)), a[1] + 0.5))
            time.sleep(0.5)
            start = time.monotonic()
            assert "Moved 1" in ai.move(game, cart, "TRADE_CART", g.map.T, b[0] + 0.5, g.map.y(*b), b[1] + 0.5)
            p = None
            while time.monotonic() < start + 2 * most and not (p and math.dist(p, (b[0] + 0.5, b[1] + 0.5)) < 2):
                p = (g.pos(cart) or (0, 0, 0))[::2]
                time.sleep(0.25)
            times.append((round(time.monotonic() - start, 1), p))
            game.command(f"kill {cart}")
        assert all(t <= most for t, _ in times), (times, most)
