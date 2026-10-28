"""A saved game keeps the military units that the player trained or upgraded in the game, and the villagers that it
trained (#2532, epic #2253): after a load they count in the population and get the next upgrade."""
import json

from test_loom import setup

from game import savegame, train


def loaded(g):
    server, h = setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return server, h


def trained():
    """The Gather of test_loom with a trained militia and villager, and the Man-at-Arms upgrade."""
    _, g = setup()
    soldier = train.summon(g, "MILITIA", (11.5, 64.0, 11.5))
    villager = train.summon(g, "VILLAGER_FEMALE", (12.5, 64.0, 12.5))
    train.research(g, {"name": "MAN_AT_ARMS_UPGRADE", "player": "Steve"})
    return g, soldier, villager


def test_a_loaded_game_has_the_trained_and_upgraded_units():
    g, soldier, villager = trained()
    server, h = loaded(g)
    assert h.soldiers == {"m": "MAN_AT_ARMS", soldier: "MAN_AT_ARMS"}
    assert villager in {o.get("uuid") for o in h.units}
    server.entities[soldier] = {"Pos": (11.5, 64.0, 11.5)}
    train.census(h)
    assert h.pop == 3                                                  # the villager and militia of the map, the trained one


def test_a_loaded_game_upgrades_the_trained_units():
    g, soldier, _ = trained()
    _, h = loaded(g)
    train.research(h, {"name": "LONG_SWORDSMAN_UPGRADE", "player": "Steve"})
    assert h.soldiers[soldier] == "LONG_SWORDSMAN"


def test_a_save_before_the_soldiers_loads():
    _, g = setup()
    d = json.loads(json.dumps(savegame.dump(g), sort_keys=True))
    for p in d["players"].values():
        p.pop("soldiers", None), p.pop("units", None)
    _, h = setup()
    savegame.load(h, d)
    assert h.soldiers == {"m": "MILITIA"}
