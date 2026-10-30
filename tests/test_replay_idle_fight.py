"""Live replay: a villager with an ORDER on an enemy unit fights in AoE2, so the idle time does not count it up to its
next record command (#4063). In de-64.3 eight P1 villagers attacked the archer 12175 at 20:32 and gave 75 of 250
idle minutes: the record has no end of the fight."""
from test_replay_eco import vill
from test_replay_idle_commands import move, replay_of


def order(t, target, player=1):
    return dict(time=t, player=player, kind="order", objects=[1], target=target, tile=[2.0, 2.0])


def play(target, later):
    r = replay_of([order(0, target), move(later, 1)])
    vill(r, "VILLAGER_MALE", 1, 1)
    vill(r, "ARCHER", 2, 8)
    vill(r, "VILLAGER_FEMALE", 1, 9)
    r.commands(r.data["timeline"][0])
    r.idle_time(0)
    return r


def test_a_villager_that_attacks_an_enemy_unit_is_not_idle():
    r = play(8, 300_000)
    r.idle_time(300_000)
    assert r.idled[1] == 0


def test_an_order_on_an_own_unit_is_idle_time():
    r = play(9, 300_000)
    r.idle_time(300_000)
    assert r.idled[1] == 300


def test_the_next_command_ends_the_fight():
    r = play(8, 100_000)
    r.idle_time(100_000)
    r.commands(r.data["timeline"][1])
    r.data["timeline"].append(move(130_000, 1))
    del r.told
    r.idle_time(130_000)
    assert r.idled[1] == 30
