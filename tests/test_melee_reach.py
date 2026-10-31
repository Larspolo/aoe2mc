"""A melee unit with an AoE2 reach (the key "melee_reach", the Kamayuk, #5242) hits as a melee unit from its reach."""
import combat

REACH = {r["name"]: r["range"] for r in combat.UNIT_ROWS if r.get("melee_reach")}


def test_a_reach_unit_is_a_melee_unit_with_its_reach_in_blocks():
    assert REACH
    for name, tiles in REACH.items():
        cmd = combat.stats_command("u", name, T=4).split()
        assert cmd[7] == "0" and f"reach={tiles * 4:g}" in cmd, cmd     # melee, no shot
        assert combat.stats(name).range == 0 and combat.range_command("u", name, 4) is None, name


def test_its_hit_takes_the_melee_armor():
    name = next(iter(REACH))
    t = combat.stats("KNIGHT")
    assert combat.damage(name, "KNIGHT", t=t._replace(pierce=99)) == combat.damage(name, "KNIGHT")


def test_the_reach_follows_the_tile_size():
    name = next(iter(REACH))
    assert f"reach={REACH[name] * 2:g}" in combat.stats_command("u", name, T=2).split()


def test_no_reach_for_a_unit_without_the_key():
    assert "reach=" not in combat.stats_command("u", "KNIGHT")
