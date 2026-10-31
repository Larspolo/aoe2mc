"""The messages of one AoE2 player go only to the Minecraft players of its team p<player>, the messages that AoE2 shows
to all players go to @a (#1307)."""
import pathlib

import pytest
from test_gather import FakeServer, grid

from game import cheats, combat, garrison, gather, monk, train

GAME = pathlib.Path(__file__).parent.parent / "game"


def setup(player):
    """A flat 30 × 30 map (tile size 1): an own villager "v", an enemy militia "foe" and an enemy house."""
    other = 3 - player
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": player, "uuid": "v", "tile": [5.5, 5.5]},
               {"kind": "unit", "name": "MILITIA", "player": other, "uuid": "foe", "tile": [8.5, 5.5]},
               {"kind": "building", "name": "HOUSE", "player": other, "footprint": [20, 4, 22, 6]}]
    server = FakeServer({"v": {"Pos": (5.5, 64.0, 5.5)}, "foe": {"Pos": (8.5, 64.0, 5.5)}, "Steve": {}})
    g = gather.Gather(server, grid([[64] * 30 for _ in range(30)], objects), player=player).setup()
    server.log.clear()
    return server, g


def sent(server, *texts):
    """The commands of the log that hold one of texts."""
    return [c for c in server.log if any(t in c for t in texts)]


@pytest.mark.parametrize("player", [1, 2])
def test_own_messages_go_to_the_own_team(player):
    server, g = setup(player)
    team = f"@a[team=p{player}] "
    g.garrisons[(10, 12, 10, 12)] = ["v"]
    garrison.out(g, (10, 12, 10, 12))
    monk.take(g, "foe")
    house = combat.target_uuid([20, 4, 22, 6])
    g.forts[house], g.fort_names[house] = (20, 64, 4, 22, 70, 6), "HOUSE"
    monk.win(g, house)
    train.research(g, {"name": "FEUDAL_AGE", "player": "Steve"})
    cheats.end("Defeat", "red")(g, "Steve")
    own = sent(server, "units came out", "A monk converts", '"Feudal Age",', '"Defeat"')
    assert len(own) == 5 and all(c.split(" ", 1)[1].startswith(team) for c in own), own
    assert sum(" title " in c for c in own) == 2


def test_messages_for_all_players_stay_for_all():
    server, g = setup(2)
    train.research(g, {"name": "FEUDAL_AGE", "player": "Steve"})
    assert [c.split(" ", 1)[1].startswith("@a ") for c in sent(server, '"fallback": "Feudal Age"}]')] == [True]
    for name in ("wonder.py", "relic_victory.py", "conquest.py"):              # wonder, relics, defeat: all see them
        text = (GAME / name).read_text()
        assert "tellraw @a " in text and "@a[team=" not in text
