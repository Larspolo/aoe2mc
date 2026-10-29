"""game/train.py, game/build.py, game/garrison.py: an Achaemenid town center becomes a Defensive Town Center (AoE2 DE
wiki "Defensive Town Center": the values of its line in game/data/train.jsonl: its effect, its arrows, and the own
units near it attack faster). It changes only the town center that researches it, and that one takes no other upgrade
of this kind (#2497)."""
import re

from menu_line import item
from test_gather import FakeServer, grid
from test_loom import menus

from game import build, combat, gather, train

A, B = (2, 5, 2, 5), (24, 27, 24, 27)                                 # the block footprints of the two town centers
UPGRADE = "DEFENSIVE_TOWN_CENTER"
ROW = next(r for r in train.ROWS if r["name"] == UPGRADE)
RATE, NEAR = ROW["attack_aura"]["rate"], ROW["attack_aura"]["range"]


class Server(FakeServer):
    """A FakeServer with the hit points of the buildings (the score aoe_hp)."""

    def command(self, cmd):
        if m := re.fullmatch(r"scoreboard players get (\S+) aoe_hp", cmd):
            self.log.append(cmd)
            return f"{m[1]} has {self.scores.get(m[1], 2400)} [aoe_hp]"
        return super().command(cmd)


def setup(civ="ACHAEMENIDS", age=("FEUDAL_AGE",)):
    """A flat 32 × 32 map (tile size 1) with two town centers of player 1, an archer next to the first one and one
    far from both."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [25.5, 25.5], "footprint": [24, 24, 27, 27]}]
    data = grid([[64] * 32 for _ in range(32)], objects)
    data["players"] = {"1": {"civ": civ}}
    server = Server({"near": {"Pos": (9.5, 64.0, 3.5)}, "far": {"Pos": (14.5, 64.0, 14.5)}})
    g = gather.Gather(server, data).setup()
    g.techs.update(age)
    g.stock.update(wood=1000, stone=1000)
    g.soldiers.update(near="ARCHER", far="ARCHER")
    return server, g


def upgrade(g, rect):
    assert train.queue(g, "Steve", rect[::2], UPGRADE) == rect
    train.tick(g, ROW["time"])


def reloads(server, uuid):
    """The reload ticks of the `aoe stats` commands of uuid in the log."""
    return [int(c.split()[10]) for c in server.log if c.startswith(f"aoe stats {uuid} ")]


def test_the_upgraded_town_center_gets_the_values_of_the_effect():
    server, g = setup()
    old = build.values(g, "TOWN_CENTER", rect=A)
    upgrade(g, A)
    new, other = build.values(g, "TOWN_CENTER", rect=A), build.values(g, "TOWN_CENTER", rect=B)
    assert g.upgraded == {A: UPGRADE} and other == old                              # only this town center
    add, times = ROW["effect"]["add"], ROW["effect"]["times"]
    assert all(getattr(new, k) == getattr(old, k) + v for k, v in add.items())
    assert all(getattr(new, k) == int(getattr(old, k) * v) for k, v in times.items())
    uuid = combat.target_uuid([A[0], A[2], A[1], A[3]])
    assert any(c.startswith(f"aoe building {uuid} {new.hp} {new.melee} {new.pierce} ") for c in server.log)
    assert f"scoreboard players set {uuid} aoe_hp {2400 + new.hp - old.hp}" in server.log   # the lost hit points stay lost
    assert server.log[-1] == f"aoe arrows {uuid} {ROW['arrows']}"                   # the arrows with no garrison
    assert not any(combat.target_uuid([B[0], B[2], B[1], B[3]]) in c for c in server.log if c.startswith("aoe "))


def test_the_other_upgrades_are_gone_at_that_town_center():
    server, g = setup()
    upgrade(g, A)
    train.open_menu(g, "Steve", A[::2])
    assert item(menus(server)[-1], "Defensive Town Center") is None
    assert item(menus(server)[-1], "Economic Town Center") is None
    assert train.queue(g, "Steve", A[::2], "ECONOMIC_TOWN_CENTER") is None
    assert train.queue(g, "Steve", B[::2], "ECONOMIC_TOWN_CENTER") == B             # another town center: yes


def test_the_units_near_it_attack_faster():
    server, g = setup()
    train.haste(g, train.HASTE_EVERY)
    assert reloads(server, "near") == []                                            # no upgrade: no change
    upgrade(g, A)
    s = train.stats(g, "ARCHER")
    fast = round(s.reload / RATE / combat.NORMAL * 20)
    train.haste(g, train.HASTE_EVERY)
    assert reloads(server, "near") == [fast] and reloads(server, "far") == []
    assert f"aoe range near {s.range} {max(1, round(s.reload / RATE / combat.NORMAL * 20))}" in server.log
    train.haste(g, train.HASTE_EVERY)
    assert reloads(server, "near") == [fast]                                        # no change: no command
    server.entities["near"]["Pos"] = (2 + 3 + NEAR + 0.5, 64.0, 3.5)                # out of its range
    train.haste(g, train.HASTE_EVERY)
    assert reloads(server, "near") == [fast, round(s.reload / combat.NORMAL * 20)]
