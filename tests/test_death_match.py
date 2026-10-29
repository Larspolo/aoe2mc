"""#2438: `run.py --play --mode death-match` is the AoE2 DE game mode "Death Match" (wiki "Deathmatch"): each player and
bot starts with the resources of the "level" of the mode (game/data/setup.jsonl)."""
from test_gather import FakeServer, grid

from game import gather, run, table, train


def settings(**given):
    return run.mode_defaults({**run.SETTINGS, **given})


LEVEL = run.MODES["death-match"]["level"]


def test_death_match_starts_with_the_resources_of_its_level():
    s = settings(mode="death-match")
    assert s["resources"] == LEVEL
    data = grid([[64] * 8 for _ in range(8)], [{"kind": "building", "name": "TOWN_CENTER", "player": p,
                                                "footprint": [p * 2, 1, p * 2 + 1, 2]} for p in (1, 2)])
    for player in (1, 2):                                              # the player and the bot: the same Gather stock
        g = gather.Gather(FakeServer({}), data, player=player, resources=s["resources"])
        assert {r: g.stock[r] for r in gather.LEVELS[LEVEL]} == gather.LEVELS[LEVEL]


def test_a_given_setting_wins_over_the_mode():
    s = settings(mode="death-match", resources="high", age="castle")
    assert s["resources"] == "high" and s["age"] == "castle"
    assert settings(mode="death-match", age="castle")["resources"] == LEVEL


def test_the_other_modes_keep_their_defaults():
    assert settings() == run.SETTINGS
    for mode, r in run.MODES.items():
        if "level" not in r:
            assert settings(mode=mode)["resources"] == run.SETTINGS["resources"], mode


def test_each_mode_default_is_a_setting_that_exists():
    for r in table.load("setup.jsonl"):
        assert r.get("level", "standard") in gather.LEVELS and r.get("age", "dark") in train.STARTS, r["name"]
