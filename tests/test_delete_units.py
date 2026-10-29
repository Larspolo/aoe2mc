"""game/stance.py and game/build.py: the item "Delete" of the stance menu and of the build menu kills each selected own
unit at once, as the AoE2 Delete key (#3451). The census counts the deaths as after a fight."""
import re

from game import build, gather, stance

from test_gather import FakeServer, grid


class KillServer(FakeServer):
    """A fake server on which the kill of a unit removes the entity: a dead unit has no position. keep: the units with
    the tag aoe2mc.keep ("Disable Object Deletion", #3777)."""
    keep = ()

    def command(self, cmd):
        if (m := re.fullmatch(r"execute as (\S+) if entity @s\[tag=!aoe2mc.keep\] run kill @s", cmd)) and m[1] not in self.keep:
            self.entities.pop(m[1], None)
        return super().command(cmd)


def setup():
    """A militia and a villager of player 1 (both selected) and a militia of player 2."""
    feet = {"m-1": (5.5, 64.0, 10.5), "v-1": (12.5, 64.0, 4.5), "e-1": (20.5, 64.0, 20.5)}
    names = {"m-1": ("MILITIA", 1), "v-1": ("VILLAGER_MALE", 1), "e-1": ("MILITIA", 2)}
    objects = [{"kind": "unit", "name": n, "player": p, "uuid": u, "tile": [0.5, 0.5]} for u, (n, p) in names.items()]
    server = KillServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.selected = {"m-1", "v-1", "e-1"}
    return server, g


def test_delete_is_in_the_stance_menu_and_the_build_menu():
    server, g = setup()
    assert [name for slot, _, name, _ in stance.items(g, "m-1") if slot == stance.DELETE] == ["Delete"]
    build.open_menu(g, "Steve")
    assert any("Delete" in c for c in server.log)


def test_delete_kills_the_own_units_only():
    server, g = setup()
    stance.open_menu(g, "Steve", "m-1")
    server.log.clear()
    g.menus["Steve"]("Steve", stance.DELETE, False)
    assert all(f"execute as {u} if entity @s[tag=!aoe2mc.keep] run kill @s" in server.log for u in ("m-1", "v-1"))
    assert not any("e-1" in c for c in server.log)                       # no command to a unit of another player
    assert "aoe menu-close Steve" in server.log


def test_after_delete_the_selection_is_empty_and_the_population_drops():
    server, g = setup()
    build.open_menu(g, "Steve")
    g.menus["Steve"]("Steve", build.DELETE, False)
    assert not g.selected & {"m-1", "v-1"}
    assert "m-1" not in g.soldiers and "v-1" not in g.villagers
    assert g.pop == 0
