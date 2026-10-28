"""#2474: `run.py --play --handicap 1=150` gives player 1 the AoE2 DE "Handicap" (AoE2 wiki, "Random map", "Team
Settings": 100 % to 200 % in steps of 5 %; it multiplies the start resources, the villager work rate and hit points, the
building hit points and the work rate of the military buildings)."""
import argparse
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import build  # noqa: E402
import civs  # noqa: E402
import combat  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402
import savegame  # noqa: E402
import train  # noqa: E402

BASE = {"food": 200, "wood": 200, "gold": 100, "stone": 200}


def g(pct=None, player=1):
    p = {"civ": "BRITONS"} | ({"handicap": pct} if pct else {})
    return types.SimpleNamespace(data={"players": {str(player): p}}, player=player, techs=set())


class FakeGame:
    kind, game_port, version, sides = "vanilla", 0, "26.3", {}

    def forceload(self):
        pass

    def command(self, c):
        pass


def test_handicap_option_multiplies_the_start_resources_of_its_player(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": {"1": {}, "2": {}}, "tile_size": 4}))
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, game, data, player, **k):
            self.data, self.player = data, player

        def setup(self):
            seen.append(self)

        def run(self, seconds):
            pass
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    run.play(FakeGame(), str(tmp_path), handicap=run.handicap_choices(["1=150"]))
    one, = seen
    assert civs.start(one, BASE) == {"food": 300, "wood": 300, "gold": 150, "stone": 300}
    assert civs.start(types.SimpleNamespace(data=one.data, player=2), BASE) == BASE     # the other player: 100 %


def test_handicap_values_of_the_lobby():
    assert run.handicap_choices(["1=100", "2=200", "3=105"]) == {1: 100, 2: 200, 3: 105}
    for bad in ("1=95", "1=210", "1=152", "1=x", "150"):
        with pytest.raises(SystemExit) as e:
            run.handicap_choices([bad])
        assert "100 to 200 in steps of 5" in str(e.value)


def test_villager_work_rate_and_build_rate():
    assert civs.work(g(150), "wood") == 1.5 * civs.work(g(), "wood")
    assert civs.build_rate(g(150), "HOUSE") == 1.5 * civs.build_rate(g(), "HOUSE")


def test_villager_hit_points():
    assert train.stats(g(150), "VILLAGER").hp == round(1.5 * train.stats(g(), "VILLAGER").hp)
    assert train.stats(g(150), "MAN_AT_ARMS").hp == train.stats(g(), "MAN_AT_ARMS").hp   # only the villagers
    o = {"name": "VILLAGER_MALE", "player": 1}
    assert combat.villager(g(150).data, o).hp == round(1.5 * combat.stats("VILLAGER").hp)
    assert combat.villager(g().data, o) is None                                       # 100 %: the plain values


def test_building_hit_points():
    assert build.values(g(150), "HOUSE").hp == round(1.5 * build.values(g(), "HOUSE").hp)
    assert combat.wall("STONE_WALL", 0, None, 1.5).hp == round(1.5 * combat.wall("STONE_WALL", 0).hp)


def test_work_rate_of_military_buildings_only():
    assert train.seconds(g(150), "MILITIA", "BARRACKS") == pytest.approx(train.seconds(g(), "MILITIA", "BARRACKS") / 1.5)
    assert train.seconds(g(150), "LOOM", "TOWN_CENTER") == train.seconds(g(), "LOOM", "TOWN_CENTER")


def test_a_save_keeps_the_handicap():
    a = argparse.Namespace(handicap=None)
    savegame.settings(a, {"settings": {"handicap": ["1=150"]}, "players": {}})
    assert run.handicap_choices(a.handicap) == {1: 150}
