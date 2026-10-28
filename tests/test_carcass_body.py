"""#3272: a killed animal shows its body (an item display) on the carcass tile until its food is gone."""
from test_meat_decay import game, kill


def bodies(server):
    return [c for c in server.log if "aoe_carcass_" in c and c.startswith("summon item_display")]


def test_a_kill_shows_a_body_on_the_carcass_tile():
    server, g = game("SHEEP", "BRITONS")
    kill(server, g)
    (tx, tz), = g.map.carcasses
    body, = bodies(server)
    assert f"aoe_carcass_{tx}_{tz}" in body and "minecraft:beef" in body
    x, _, z = map(float, body.split()[2:5])
    assert int(x // g.map.T) == tx and int(z // g.map.T) == tz


def test_the_body_goes_when_the_food_is_gone():
    server, g = game("DEER", "FRANKS")
    kill(server, g)
    (tx, tz), = g.map.carcasses
    g.villagers["v"].state = "idle"
    kill_cmd = f"kill @e[type=item_display,tag=aoe_carcass_{tx}_{tz}]"
    g.decay(10.0)
    assert server.log.count(kill_cmd) == 1                           # only the clear before the summon
    g.decay(100000.0)
    assert g.map.carcasses[(tx, tz)] == 0 and server.log.count(kill_cmd) == 2


def test_a_predator_leaves_no_body():
    server, g = game("WOLF", "MAGYARS", hp=8.0)
    kill(server, g)
    assert not g.map.carcasses and not bodies(server)
