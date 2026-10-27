"""A 48 x 48 play-test map for one owner session: player 1 (Britons) in the north-west with a lake, a dock and a
transport ship; player 2 (Franks, the bot) in the south-east with 5 militia for the first wave."""
import sys

sys.path.insert(0, "/Users/polo/aoe2mc/tools")
from scenarios import (BuildingInfo, Civilization, OtherInfo, PlayerId, TerrainId, UnitInfo,  # noqa: E402
                       new_scenario, save)

scn = new_scenario(48)
scn.player_manager.active_players = 2
scn.player_manager.players[1].civilization = Civilization.BRITONS
scn.player_manager.players[2].civilization = Civilization.FRANKS
for t in scn.map_manager.terrain:
    x, y = t.x, t.y
    d = max(abs(x - 8), abs(y - 33))                       # the lake in the south-west
    if d <= 3:
        t.terrain_id = TerrainId.WATER_DEEP
    elif d <= 5:
        t.terrain_id = TerrainId.WATER_SHALLOW
    elif d == 6:
        t.terrain_id = TerrainId.BEACH
    elif y <= 1 or x >= 46 or (x <= 1 and y <= 20):
        t.terrain_id = TerrainId.FOREST_OAK
um = scn.unit_manager
for x in range(3, 22, 2):                                  # wood lines of both players
    um.add_unit(PlayerId.GAIA, OtherInfo.TREE_OAK.ID, x=x + 0.5, y=3.5)
for y in range(26, 45, 2):
    um.add_unit(PlayerId.GAIA, OtherInfo.TREE_OAK.ID, x=44.5, y=y + 0.5)
for (cx, cy), p in (((12, 12), PlayerId.ONE), ((36, 36), PlayerId.TWO)):
    s = 1 if p == PlayerId.ONE else -1
    for dx, dy, b in ((0, 0, BuildingInfo.TOWN_CENTER), (-5, -4, BuildingInfo.HOUSE), (-2, -5, BuildingInfo.HOUSE)):
        um.add_unit(p, b.ID, x=cx + s * dx, y=cy + s * dy)
    for dx, dy, u in ((-1.5, 3.5, UnitInfo.VILLAGER_MALE), (0.5, 3.5, UnitInfo.VILLAGER_FEMALE),
                      (2.5, 3.5, UnitInfo.VILLAGER_MALE), (3.5, 1.5, UnitInfo.VILLAGER_FEMALE),
                      (3.5, -0.5, UnitInfo.VILLAGER_MALE), (3.5, -2.5, UnitInfo.VILLAGER_FEMALE)):
        um.add_unit(p, u.ID, x=cx + s * dx, y=cy + s * dy)
    for dx, dy, o in ((6.5, 4.5, OtherInfo.FORAGE_BUSH), (7.5, 4.5, OtherInfo.FORAGE_BUSH),
                      (6.5, 5.5, OtherInfo.FORAGE_BUSH), (7.5, 5.5, OtherInfo.FORAGE_BUSH),
                      (8.5, -3.5, OtherInfo.GOLD_MINE), (9.5, -3.5, OtherInfo.GOLD_MINE), (8.5, -2.5, OtherInfo.GOLD_MINE),
                      (-6.5, 2.5, OtherInfo.STONE_MINE), (-6.5, 3.5, OtherInfo.STONE_MINE)):
        um.add_unit(PlayerId.GAIA, o.ID, x=cx + s * dx, y=cy + s * dy)
    for dx, dy in ((-3.5, 5.5), (-2.5, 6.5), (-1.5, 5.5), (-3.5, 6.5)):
        um.add_unit(PlayerId.GAIA, UnitInfo.SHEEP.ID, x=cx + s * dx, y=cy + s * dy)
um.add_unit(PlayerId.ONE, BuildingInfo.BARRACKS.ID, x=19.5, y=12.5)          # the building to repair (#1332)
um.add_unit(PlayerId.ONE, BuildingInfo.DOCK.ID, x=8.5, y=27.5)               # on the north beach of the lake
um.add_unit(PlayerId.ONE, UnitInfo.TRANSPORT_SHIP.ID, x=8.5, y=30.5)
for x in (11.5, 12.5, 13.5):                                                  # 3 militia for the transport ship (#1492)
    um.add_unit(PlayerId.ONE, UnitInfo.MILITIA.ID, x=x, y=25.5)
for x in (31.5, 32.5, 33.5, 34.5, 35.5):                                      # the first wave of the bot (bot.GROUP)
    um.add_unit(PlayerId.TWO, UnitInfo.MILITIA.ID, x=x, y=30.5)
save(scn, sys.argv[1], "owner_loop.aoe2scenario")
print("saved", sys.argv[1])
