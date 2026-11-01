"""The camera step of the tutorial (#5503): done when the player turned the camera mode on and then off."""
from game import camera, tutorial


class G:
    paper, who = True, "@a"

    def __init__(self):
        self.active, self.log = False, []
        self.map = type("M", (), {"ground": [[64]], "n": 4})()

    def command(self, c):
        self.log.append(c)
        if c.startswith("aoe camera Steve "):                         # on with its floor, or off
            self.active = c.split()[3] == "on"
        return "Camera: on" if self.active else ""


def row():
    return next(r for r in tutorial.STEPS if r["name"] == "camera")


def test_the_camera_step_follows_the_select_step():
    names = [r["name"] for r in tutorial.STEPS]
    assert names.index("camera") == names.index("select") + 1


def test_the_step_is_done_after_on_and_off():
    g = G()
    assert not tutorial.camera(g, row())
    camera.click(g, "Steve")
    assert not tutorial.camera(g, row())
    camera.click(g, "Steve")
    assert tutorial.camera(g, row())
