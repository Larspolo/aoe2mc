"""game/gather.py: a group item click on an own villager is a group click, not a unit click (#5571)."""
from test_control_groups import GroupServer
from test_select_type import setup


def talk(server, g, n, sneak=False):
    """Steve right clicks a villager with the item of group n: only the talk statistic counts."""
    fake = GroupServer(server, n, sneak)
    fake.command, server.command = server.command, fake
    server.scores["aoe_talk"] = 1
    try:
        for name in g.clicks():
            g.click(name)
    finally:
        server.command = fake.command
    return server.log


def test_shift_click_on_a_unit_saves_the_group_and_opens_no_menu():
    server, g = setup()
    g.choose({"v-1"})
    log = talk(server, g, 1, sneak=True)
    assert g.groups == {1: {"v-1"}}
    assert not any(c.startswith("data get entity Steve Rotation") for c in log)   # no ray: no unit click, no menu


def test_click_on_a_unit_selects_the_group():
    server, g = setup()
    g.choose({"m-1"})
    talk(server, g, 2, sneak=True)
    g.choose({"v-1"})
    talk(server, g, 2)
    assert g.selected == {"m-1"}
