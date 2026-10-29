"""#2686 (epic #2263): a Battle Royale game starts as in AoE2 DE (wiki "Battle Royale"): in the Post-Imperial Age, with
the High resources and no stone, and with no town center and no villagers."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import battle_royale  # noqa: E402
import combat  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402
from test_battle_royale import fake  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

TC = [4, 4, 8, 8]


def test_the_mode_starts_with_the_resources_of_its_level():
    assert run.mode_defaults(dict(run.SETTINGS, mode="battle-royale"))["resources"] == run.MODES["battle-royale"]["level"]
    assert run.mode_defaults(dict(run.SETTINGS, mode="battle-royale", resources="low"))["resources"] == "low"


def player(resources):
    data = grid([[64] * 16 for _ in range(16)], [])
    g = gather.Gather(FakeServer({}), data, resources=resources).setup()
    battle_royale.start(g)
    return g


def test_a_player_has_the_high_resources_and_no_stone():
    g = player("high")
    high = gather.LEVELS["high"]
    assert g.stock["stone"] == 0 and all(g.stock[r] == high[r] for r in ("food", "wood", "gold"))
    assert f"scoreboard players set Stone {g.board} 0" in g.game.log
    assert player("infinite").stock["stone"] == gather.LEVELS["infinite"]["stone"]   # infinite: the stone stays


def test_the_town_centers_and_the_villagers_of_the_players_go():
    g = fake()
    g.data["objects"] = [
        dict(kind="building", name="TOWN_CENTER", player=1, footprint=TC),
        dict(kind="building", name="TOWN_CENTER", player=0, footprint=[10, 10, 14, 14]),   # Gaia keeps its own
        dict(kind="building", name="HOUSE", player=1, footprint=[0, 0, 2, 2]),
        dict(kind="unit", name="VILLAGER_MALE", player=2, uuid="v2"),
        dict(kind="unit", name="VILLAGER_FEMALE", player=0, uuid="v0"),
        dict(kind="unit", name="SCOUT_CAVALRY", player=1, uuid="s1")]
    tc = combat.target_uuid(TC)
    g.forts, g.villagers, g.enemies = {tc: (4, 64, 4, 7, 70, 7)}, {"v2": None}, {"v2": "VILLAGER_MALE", "s1": "X"}
    freed = []
    g.free = freed.append                                              # Gather.free frees the footprint (#3113)
    battle_royale.start(g)
    assert [c for c in g.log if c.startswith(("aoe destroy", "kill"))] == [f"aoe destroy {tc}", "kill v2"]
    assert freed == [tc] and g.sieged == set() and g.villagers == {} and g.enemies == {"s1": "X"}
