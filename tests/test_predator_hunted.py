"""Villagers whom the player sends at an awake wolf kill it, and the wolf gives no food (#3672)."""
import pytest

from game import gather


def test_a_wolf_is_a_predator_with_no_food():
    assert all(gather.predator(n) and gather.hunt_food(n) == 0 for n in ("WOLF", "GREY_WOLF"))


@pytest.mark.mc
def test_three_villagers_kill_an_awake_wolf_on_paper(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import contextlib
    import io
    import json
    import time

    import aoe2mc
    from game import combat, run
    m = {"size": 16, "terrain": [[0] * 16 for _ in range(16)], "players": {"1": {"civ": "Britons"}},
         "objects": [{"name": "TOWN_CENTER", "player": 1, "x": 4, "y": 4},
                     *({"name": "VILLAGER_MALE", "player": 1, "x": 8.5 + i, "y": 8.5} for i in range(3)),
                     {"name": "GREY_WOLF", "player": 0, "x": 9.5, "y": 11.5}]}
    (tmp_path / "m.json").write_text(json.dumps(m))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(str(tmp_path / "m.json"), str(tmp_path / "W"))
    data = json.load(open(tmp_path / "W" / "aoe2mc.json"))
    wolf = next(o["uuid"] for o in data["objects"] if o["name"] == "GREY_WOLF")
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        end = time.time() + 60                                         # entities load in other threads
        while len((g := gather.Gather(game, data, tick=0.05, start={}).setup()).villagers) < 3:
            assert time.time() < end, "the villagers did not load"
            time.sleep(1)
        combat.setup(game, data)                                       # the wolf wakes up
        food = game.command("scoreboard players get Food aoe_res")
        assert "passed" in game.command(f"execute if entity {wolf}")
        g.selected = set(g.villagers)
        g.hunt(wolf)
        end = time.time() + 60 / 1.7                                   # 60 game seconds at Normal speed
        while "passed" in game.command(f"execute if entity {wolf}"):
            assert time.time() < end, f"the wolf lives: {game.command(f'data get entity {wolf} Health')}"
            g.step()
        for _ in range(40):                                            # the hunters do not gather a carcass
            g.step()
        assert not any(g.map.carcasses.values()), g.map.carcasses
        assert game.command("scoreboard players get Food aoe_res") == food
