"""game/gather.py: control groups on hotbar items 1-5 (#779, owner choice #745)."""
import json
import shutil

import pytest
from test_lang_orders import plain_log
from test_select_type import setup

from game import gather, lang


class GroupServer:
    """The FakeServer of test_select_type with a group item in the main hand of Steve and a shift key."""

    def __init__(self, server, hand=None, sneak=False):
        self.server, self.hand, self.sneak = server, hand, sneak

    def __call__(self, cmd):
        if cmd.startswith("execute if items entity Steve weapon.mainhand"):
            self.server.log.append(cmd)
            return "Test passed, count: 1" if f"aoe_group:{self.hand}}}" in cmd else "Test failed"
        if cmd.startswith("execute as Steve if predicate"):
            self.server.log.append(cmd)
            return "Test passed" if self.sneak else "Test failed"
        return self.command(cmd)


def use(server, g, n, sneak=False):
    """Steve right clicks with the item of group n (shift: sneak)."""
    fake = GroupServer(server, n, sneak)
    fake.command, server.command = server.command, fake
    server.scores["aoe_use"] = 1
    try:
        for name in g.clicks():
            g.click(name)
    finally:
        server.command = fake.command
    return server.log


def test_each_player_gets_the_group_items_in_the_hotbar():
    server, g = setup()
    server.log.clear()
    g.clicks()
    give = [c for c in server.log if "item replace" in c and "aoe_group" in c]   # not the Game menu item (#1588)
    assert [c.split()[7] for c in give] == ["hotbar.4", "hotbar.5", "hotbar.6", "hotbar.7", "hotbar.8"]
    assert 'item_name="Group 3 (empty)"' in give[2] and "custom_data={aoe_group:3}" in give[2]
    assert any("carrot_on_a_stick[!custom_data]" in c for c in plain_log(server.log))   # a group item is not the click item
    server.log.clear()
    g.clicks()
    assert not any("item replace" in c for c in plain_log(server.log))            # not each tick


def test_shift_click_saves_and_click_selects_a_group():
    server, g = setup()
    g.choose({"m-1", "a-1"})
    log = use(server, g, 2, sneak=True)
    assert g.groups == {2: {"m-1", "a-1"}} and 'title Steve actionbar ' + json.dumps(lang.text("aoe2mc.gather.group_saved", 2, 2)) in log
    g.choose({"v-1"})
    log = use(server, g, 2)
    assert g.selected == {"m-1", "a-1"} and g.bar == "a-1"
    assert all(f"tag {u} add {gather.SELECT}" in log for u in ("m-1", "a-1")) and f"tag v-1 remove {gather.SELECT}" in log
    assert "data merge entity m-1 {Glowing:1b}" in log
    assert not any(c.startswith("data get entity Steve Rotation") for c in log)   # a group click casts no ray


def test_a_dead_unit_leaves_its_group():
    server, g = setup()
    g.choose({"m-1", "m-2"})
    use(server, g, 1, sneak=True)
    del server.entities["m-2"]
    use(server, g, 1)
    assert g.selected == {"m-1"} and g.groups[1] == {"m-1"}


def test_an_empty_group_clears_the_selection():
    server, g = setup()
    g.choose({"m-1"})
    log = use(server, g, 4)
    assert g.selected == set() and g.bar is None and 'title Steve actionbar ' + json.dumps(lang.text("aoe2mc.gather.group", 4, 0)) in log


def test_a_click_without_a_group_item_casts_the_ray():
    server, g = setup()
    server.entities["Steve"] = {"Pos": (5.5, 64.0, 13.5), "Rotation": (180.0, 10.0)}
    log = use(server, g, None)
    assert not g.groups and any(c.startswith("data get entity Steve Rotation") for c in log)


@pytest.mark.mc
def test_the_group_commands_work_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import json

    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    data = json.load(open(world / "aoe2mc.json"))
    with run.Game(world) as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        sent = []
        command = game.command
        game.command = lambda c: sent.append((c, command(c))) or sent[-1][1]
        g.clicks()
        g.group_in_hand("aoe2mc")                                      # no player: the commands must parse
        g.command(f"execute as @a if predicate {gather.SNEAK}")
        v, = g.villagers.values()
        g.choose({v.uuid})
        g.group("aoe2mc", 1, True)
        g.choose(set())
        g.group("aoe2mc", 1, False)
        assert g.selected == {v.uuid}
        bad = [(c, out) for c, out in sent if any(w in out for w in ("Unknown", "Incorrect", "Invalid", "Expected", "Failed to parse"))]
        assert not bad, bad
