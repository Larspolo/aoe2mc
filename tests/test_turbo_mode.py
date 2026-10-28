"""The AoE2 DE setting "Turbo Mode" of the game program (#2359, epic #2263): `game/run.py --play --turbo`. AoE2 wiki
"Turbo Random Map": the buildings work 2.5 times faster (not for villagers, trade carts, trade cogs and fishing ships),
the villagers and fishing ships gather 2.5 times faster and carry 2.5 times as much, and the villagers build 2.5 times
faster (not castles, towers and wonders). Fake server."""
import pytest
from test_build_site import site_map

from game import build, civs, fleet, run, train


def game(turbo=True):
    server, g = site_map()
    g.techs |= set(build.AGE_TECHS[:2])
    g.data["turbo"] = turbo
    return g


def test_the_buildings_train_and_research_faster_but_not_villagers():
    f = civs.TURBO["turbo"]
    for name in ("MILITIA", "ARCHER", "LOOM"):
        assert train.seconds(game(), name) * f == pytest.approx(train.seconds(game(False), name)), name
    for name in ("VILLAGER_MALE", "TRADE_CART", "FISHING_SHIP"):
        assert train.seconds(game(), name) == train.seconds(game(False), name), name


def test_a_house_builds_faster_but_not_a_castle():
    f, t = civs.TURBO["turbo"], build.BUILD_TIMES["HOUSE"]
    g = game()
    g.stock.update(wood=500, stone=1000)
    house = build.found(g, "HOUSE", (12, 14, 8, 10))
    assert not build.rise(g, house, t / f - 0.01) and build.rise(g, house, 0.02)
    castle = build.found(g, "HOUSE", (2, 4, 2, 4))
    castle.update(name="CASTLE", progress=0.0)                         # a castle site: no Turbo Mode
    build.rise(g, castle, build.BUILD_TIMES["CASTLE"] / f)
    assert castle["progress"] == pytest.approx(1 / f)


def test_the_villagers_and_fishing_ships_gather_faster_and_carry_more():
    f = civs.TURBO["turbo"]
    g, h = game(), game(False)
    assert g.work_time("wood") * f == pytest.approx(h.work_time("wood"))
    assert g.limit("wood") == round(h.limit("wood") * f)
    fish = next(iter(g.map.shore), (0, 0))
    assert fleet.rate(g, fish) == pytest.approx(fleet.rate(h, fish) * f)
    assert fleet.carry(g) == round(fleet.carry(h) * f)


def test_run_offers_the_setting(capsys):
    with pytest.raises(SystemExit):
        run.main(["--help"])
    assert "--turbo" in capsys.readouterr().out
