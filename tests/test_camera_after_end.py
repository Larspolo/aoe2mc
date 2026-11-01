"""After the end of a game the camera item still switches the camera mode, and other items do nothing (#5538)."""
import types

from test_camera import Server

from game import camera


class EndServer(Server):
    """Server with the use statistic of Steve and the item in his hand (camera or not)."""

    def __init__(self):
        super().__init__()
        self.used, self.camera = 0, True

    def command(self, cmd):
        if cmd == "list":
            return "There are 1 of a max of 8 players online: Steve"
        if cmd == "scoreboard players get Steve aoe_use":
            return f"Steve has {self.used} [aoe_use]"
        if cmd == "scoreboard players reset Steve aoe_use":
            self.used = 0
        if cmd.startswith("execute if items entity Steve weapon.mainhand") and not self.camera:
            return "Test failed"
        return super().command(cmd)


def ended():
    s = EndServer()
    g = types.SimpleNamespace(command=s.command, map=types.SimpleNamespace(ground=[[64] * 4] * 4, n=4), paper=True,
                              who="@a", ended="Victory")
    g.people = lambda: ["Steve"]
    return s, g


def test_a_camera_click_after_the_end_switches_the_mode_on_and_off():
    s, g = ended()
    s.used = 1
    assert camera.after_end(g) == ["Steve"] and s.on
    assert camera.after_end(g) == [] and s.on                          # no new click: no change
    s.used = 1
    assert camera.after_end(g) == ["Steve"] and not s.on


def test_a_click_of_the_order_item_after_the_end_does_nothing():
    s, g = ended()
    s.used, s.camera = 1, False
    assert camera.after_end(g) == [] and not s.on
    assert not [c for c in s.log if c.startswith("aoe camera Steve ")] and s.used == 0
