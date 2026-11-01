from test_cheats import game

from game import cheats


def test_give_gold_is_robin_hood(tiny_world):
    server, g = game(tiny_world, True)
    assert ",give%20gold," in "\n".join(server.log)
    server.scores["aoe_cheat"] = cheats.NAMES.index("give gold") + 1
    assert cheats.clicks(g) == [("Steve", "give gold")]
    assert g.stock["gold"] == cheats.CODES["robin hood"]["gold"]


def test_give_codes_map_to_resource_cheats():
    for r, code in cheats.GIVE.items():
        assert cheats.CODES[f"give {r}"] == cheats.CODES[code] and r in cheats.CODES[code]
