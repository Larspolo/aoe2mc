"""game/build.py: the build menu item "Seek Shelter" sends only the selected villagers into the nearest own building
with room, as in AoE2 DE (#3440). The other villagers keep working."""
import json

from menu_line import item
from test_garrison_game import TC, TOWER, setup
from test_train_menu import menus

from game import build, combat


def seek(g, player="Steve"):
    build.open_menu(g, player)
    g.menus[player](player, build.SHELTER, False)


def test_only_the_selected_villagers_seek_shelter_and_a_soldier_stays():
    server, g = setup(villagers=6)
    g.soldiers["m0"] = "MILITIA"
    server.entities["m0"] = {"Pos": (5.5, 64.0, 9.5)}
    g.choose({"v0", "v1", "v2", "m0"}, "v0")
    seek(g)
    assert set(g.entering) == {"v0", "v1", "v2"} and set(g.entering.values()) <= {TC, TOWER}
    assert all(g.villagers[f"v{k}"].state != "garrison" for k in (3, 4, 5))
    assert "playsound minecraft:block.bell.use master Steve" not in server.log
    assert "tellraw Steve " + json.dumps({"text": "3 villagers seek shelter", "color": "gray"}) in server.log


def test_a_selected_villager_far_from_all_buildings_keeps_working():
    server, g = setup(villagers=3)
    far = combat.sight("TOWN_CENTER") * g.map.T
    server.entities["v2"]["Pos"] = (3.5, 64.0, 3.5 + far + 3)      # out of the sight of the town center
    g.choose({"v0", "v1", "v2"}, "v0")
    seek(g)
    assert set(g.entering) == {"v0", "v1"} and g.villagers["v2"].state != "garrison"
    assert any("2 villagers seek shelter" in c for c in server.log)


def test_the_menu_keeps_each_building_in_its_slot():
    before = [it[0] for it in build.items()]
    server, g = setup(villagers=1)
    build.open_menu(g, "Steve")
    assert [it[0] for it in build.items()] == before == list(range(len(build.MENU)))
    assert build.SHELTER >= len(build.MENU) and build.SHELTER != build.DELETE
    assert item(menus(server)[-1], "Seek Shelter").startswith(f"{build.SHELTER}:oak_door:Seek Shelter")
