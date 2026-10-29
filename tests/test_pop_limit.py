"""The AoE2 DE setting "Population limit" of the game program (#2266, epic #2263): `game/run.py --pop-limit N` sets the
highest population of each player (AoE2 wiki "Random map": 25 to 250 in steps of 25, 300, 400 and 500; default 200)."""
import pytest
from test_gather import FakeServer, grid
from test_train_population import train_all

from game import gather, run, train


def setup(people, pop_limit=None):
    """A flat 24 × 24 map (tile size 1): a town center and 25 houses of player 1 and `people` villagers."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]}]
    objects += [{"kind": "building", "name": "HOUSE", "player": 1, "tile": [1 + 2 * (i % 10), 10 + 2 * (i // 10)],
                 "footprint": [2 * (i % 10), 9 + 2 * (i // 10), 2 + 2 * (i % 10), 11 + 2 * (i // 10)]} for i in range(25)]
    objects += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{i}", "tile": [7.5, 7.5]}
                for i in range(people)]
    server = FakeServer({f"v{i}": {"Pos": (7.5, 64.0, 7.5)} for i in range(people)})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), pop_limit=pop_limit).setup()
    g.stock["food"] = 1000
    return server, g


def test_a_town_center_trains_no_unit_at_the_limit_of_100_and_the_sidebar_shows_it():
    server, g = setup(100, pop_limit=100)
    assert g.pop == 100 and train.limit(g) == 100 and "scoreboard players set Limit aoe_res 100" in server.log
    train.queue(g, "Steve", (3, 3))
    assert train_all(g, server, train.TRAIN_TIMES["VILLAGER_MALE"] + 5) == [] and g.pop == 100
    assert any("(100/100): no more units." in c for c in server.log)


def test_below_the_limit_it_trains_and_the_default_is_200():
    server, g = setup(99, pop_limit=100)
    train.queue(g, "Steve", (3, 3))
    assert len(train_all(g, server, train.TRAIN_TIMES["VILLAGER_MALE"] + 5)) == 1 and g.pop == 100
    _, g = setup(0)
    assert train.max_pop(g) == train.LIMIT == 200
    assert train.limit(g) == train.HOUSING["TOWN_CENTER"] + 25 * train.HOUSING["HOUSE"]


def test_the_cheat_raises_a_set_limit_to_1000():
    _, g = setup(0, pop_limit=50)
    assert train.max_pop(g) == 50
    g.pop_cap = 1000                                                   # "my cpu can handle it" (cheats.py)
    assert train.max_pop(g) == 1000


def test_run_takes_only_the_aoe2_values(capsys):
    assert [run.pop_limit(str(n)) for n in (25, 100, 250, 300, 500)] == [25, 100, 250, 300, 500]
    for bad in ("30", "275", "0", "1000", "x"):
        with pytest.raises(SystemExit):
            run.main(["WORLD", "--play", "--pop-limit", bad])
        assert "no AoE2 population limit" in capsys.readouterr().err, bad


def test_play_gives_the_limit_to_each_gather(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text("{}")
    calls = []

    def made(game, data, **kw):
        calls.append(kw.get("pop_limit"))
        raise StopIteration
    monkeypatch.setattr("gather.Gather", made)                       # the module that run.play imports
    with pytest.raises(StopIteration):
        run.play(type("Game", (), {"forceload": lambda self: None})(), str(tmp_path), pop_limit=75)
    assert calls == [75]
