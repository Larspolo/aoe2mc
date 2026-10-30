"""game/gather.py: a click with selected military units on an enemy unit sends them to attack it (#516)."""
import math

from test_gather import FakeServer, grid

from game import ai, gather


def setup():
    objects = [{"kind": "unit", "name": n, "player": p, "uuid": u, "tile": [0.5, 0.5]}
               for u, n, p in (("s-1", "MILITIA", 1), ("s-2", "ARCHER", 1), ("v-1", "VILLAGER_MALE", 1),
                               ("own", "SPEARMAN", 1), ("foe", "KNIGHT", 2), ("deer", "DEER", 0))]
    feet = {"s-1": (5.5, 64.0, 10.5), "s-2": (15.5, 64.0, 10.5), "v-1": (2.5, 64.0, 2.5),
            "own": (10.5, 64.0, 5.5), "foe": (10.5, 64.0, 14.5), "deer": (18.5, 64.0, 18.5)}
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    g = gather.Gather(server, grid([[64] * 20 for _ in range(20)], objects)).setup()
    return server, g


def click(server, g, at, look):
    """Steve stands at block `at` and clicks the unit at block `look`."""
    eye = (at[0], 64.0, at[1])
    dx, dz, dy = look[0] - eye[0], look[1] - eye[2], 1 - 1.62
    yaw, pitch = math.degrees(math.atan2(-dx, dz)), -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    server.entities["Steve"] = {"Pos": eye, "Rotation": (yaw, pitch)}
    server.log.clear()
    g.click("Steve")
    return server.log


def test_military_units():
    assert [n for n in ("MILITIA", "KNIGHT", "WAR_DOG", "BATTERING_RAM") if gather.military(n)] == \
        ["MILITIA", "KNIGHT", "WAR_DOG", "BATTERING_RAM"]
    assert not any(gather.military(n) for n in ("VILLAGER_FEMALE", "MONK", "TRADE_CART", "SHEEP", "WOLF", "KING"))


def test_click_on_an_enemy_sends_the_selected_soldiers_to_attack():
    server, g = setup()
    assert set(g.soldiers) == {"s-1", "s-2", "own"} and set(g.enemies) == {"foe"}
    click(server, g, (5.5, 13.5), (5.5, 10.5))
    click(server, g, (15.5, 13.5), (15.5, 10.5))                       # a second soldier: added
    assert g.selected == {"s-1", "s-2"}
    log = click(server, g, (10.5, 17.5), (10.5, 14.5))
    attacks = [c for c in log if c.startswith("aoe attack")]
    assert attacks == [f"aoe attack @e[tag={gather.SELECT}] foe"]
    assert log.index(ai.speed_command("s-1", "MILITIA", 1)) < log.index(attacks[0])
    assert ai.speed_command("s-2", "ARCHER", 1) in log
    assert g.selected == {"s-1", "s-2"}                                 # the selection stays


def test_click_on_an_own_unit_selects_it_and_sends_no_attack():
    server, g = setup()
    click(server, g, (5.5, 13.5), (5.5, 10.5))
    log = click(server, g, (10.5, 8.5), (10.5, 5.5))                    # an own spearman: added, no attack
    assert not [c for c in log if c.startswith("aoe attack")] and g.selected == {"s-1", "own"}
    assert f"tag own add {gather.SELECT}" in log
    log = click(server, g, (2.5, 5.5), (2.5, 2.5))                      # a villager: only the villager
    assert g.selected == {"v-1"} and f"tag s-1 remove {gather.SELECT}" in log
    log = click(server, g, (10.5, 17.5), (10.5, 14.5))                  # a villager is no army: no attack
    assert not [c for c in log if c.startswith("aoe attack")] and g.selected == {"v-1"}
