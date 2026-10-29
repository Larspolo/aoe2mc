"""game/combat.py: the class "Stone Defense" (combat.STONE, #1590): the stone walls and gates, the towers and the
buildings with "stone" in the data, not the palisades. The plugin reads the classes of a building."""
from game import combat


def test_the_stone_defense_class_and_the_building_command():
    stone = {k for k, s in combat.BUILDINGS.items() if combat.STONE in s.classes}
    assert {k for k in combat.BUILDINGS if k.endswith("_TOWER") or k == "KEEP"} | combat.STONE_ROWS <= stone
    assert {k for k in combat.WALLS if combat.STONE in combat.wall(k, 0).classes} == \
        {k for k in combat.WALLS if not k.startswith("PALISADE")}
    cmd = combat.building(combat.target_uuid([0, 0, 2, 2]), "WATCH_TOWER", 1, (0, 64, 0, 1, 70, 1), 4)[-1]
    assert cmd.split()[16] == ",".join(combat.stats("WATCH_TOWER").classes)   # the plugin reads the classes
    house = combat.building(combat.target_uuid([4, 4, 6, 6]), "HOUSE", 1, (0, 64, 0, 1, 70, 1), 4)[-1]
    if combat.stats("HOUSE").classes == ("building", combat.STANDARD):
        assert house.split()[-1] == "1"                                 # the default classes: no class text
