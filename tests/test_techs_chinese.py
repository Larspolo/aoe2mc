"""Great Wall and Rocketry (#4102): the castle of the Chinese researches them with the values of the AoE2 DE wiki
("Unique technology"). Great Wall (Castle Age: 400 wood, 200 stone, 40 s): walls and towers +30% HP. Rocketry (Imperial
Age: 935 food, 765 gold, 60 s): Scorpions, Rocket Carts and Lou Chuans +25% attack. Only the Chinese have them (the key
"civ" of data/train.jsonl)."""
from test_train_castle import menus, setup

from game import build, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_chinese_researches_them():
    server, g = setup("CHINESE", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'GREAT_WALL')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "GREAT_WALL") is None
    server, g = setup("CHINESE", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'ROCKETRY')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "ROCKETRY") is None


def test_great_wall_adds_hp_to_walls_and_towers_only():
    server, g = setup("CHINESE", food=3000, wood=3000, gold=3000, ages=2)
    g.stock.update(stone=3000)
    stone_wall = build.values(g, "STONE_WALL").hp
    guard_tower = build.values(g, "GUARD_TOWER").hp
    castle = build.values(g, "CASTLE").hp
    assert train.queue(g, "Steve", CASTLE, "GREAT_WALL")
    train.tick(g, train.seconds(g, "GREAT_WALL", "CASTLE"))
    assert "GREAT_WALL" in g.techs
    assert build.values(g, "STONE_WALL").hp > stone_wall
    assert build.values(g, "GUARD_TOWER").hp > guard_tower
    assert build.values(g, "CASTLE").hp == castle                   # not a wall or a tower


def test_rocketry_adds_attack_to_scorpions_and_rocket_carts_only():
    server, g = setup("CHINESE", food=3000, wood=3000, gold=3000, ages=3)
    scorpion = train.stats(g, "SCORPION").attack
    mangonel = train.stats(g, "MANGONEL")
    assert train.queue(g, "Steve", CASTLE, "ROCKETRY")
    train.tick(g, train.seconds(g, "ROCKETRY", "CASTLE"))
    assert "ROCKETRY" in g.techs
    assert train.stats(g, "SCORPION").attack > scorpion
    assert train.stats(g, "MANGONEL") == mangonel                   # not a scorpion, a rocket cart or a Lou Chuan
