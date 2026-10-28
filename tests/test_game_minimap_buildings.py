"""The buildings of the game program on the minimap (#2582, epic #2580): on Paper a foundation draws the square of its
footprint in the player color (`aoe minimap building`), a fallen building removes it (`aoe minimap unbuild`), and
run.play draws the buildings of the start once."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import build  # noqa: E402
import combat  # noqa: E402
import gather  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402
from test_wonder import targets  # noqa: E402

START = [{"kind": "building", "name": "HOUSE", "player": 2, "footprint": [10, 10, 12, 12]},
         {"kind": "building", "name": "HOUSE", "player": 1, "footprint": [2, 10, 4, 12]},
         {"kind": "building", "name": "RUINS", "player": 0, "footprint": [16, 16, 18, 18]}]


def game(kind="paper"):
    server = FakeServer({"Steve": {}})
    server.kind = kind
    data = grid([[64] * 20 for _ in range(20)], START)
    data.update(level_height=1, players={"1": {"color": "blue", "arch": "western"}, "2": {"color": "red"}})
    g = gather.Gather(server, data).setup()
    g.stock.update(wood=1000)
    server.log.clear()
    return server, g


def test_a_foundation_draws_its_square_in_the_player_color():
    server, g = game()
    build.found(g, "HOUSE", (4, 6, 14, 16))                            # x0, x1, z0, z1
    assert server.log.count("aoe minimap building 4 14 6 16 p1") == 1


def test_a_fallen_building_leaves_the_minimap():
    server, g = game()
    targets(server, set())                                             # the plugin removed its target
    g.sieged.add(combat.target_uuid([10, 10, 12, 12]))
    g.fall()
    assert "aoe minimap unbuild 10 10" in server.log


def test_the_start_draws_the_buildings_of_the_map_and_the_sites_but_not_gaia():
    _, g = game()
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": (4, 6, 14, 16)})   # a site of a loaded game
    assert build.minimap(g) == ["aoe minimap building 2 10 4 12 p1", "aoe minimap building 4 14 6 16 p1",
                                "aoe minimap building 10 10 12 12 p2"]


def test_run_play_sends_the_start_buildings_once(tmp_path, monkeypatch):
    from test_game_minimap import commands
    monkeypatch.setattr(build, "minimap", lambda g: ["aoe minimap building 1 2 3 4 p1"])
    sent = commands(tmp_path, monkeypatch, "paper")
    assert sent.count("aoe minimap building 1 2 3 4 p1") == 1 and sent.index("aoe minimap on") < \
        sent.index("aoe minimap building 1 2 3 4 p1")


def test_vanilla_draws_nothing():
    server, g = game("vanilla")
    build.found(g, "HOUSE", (4, 6, 14, 16))
    targets(server, set())
    g.sieged.add(combat.target_uuid([10, 10, 12, 12]))
    g.fall()
    assert not [c for c in server.log if "aoe minimap" in c]
