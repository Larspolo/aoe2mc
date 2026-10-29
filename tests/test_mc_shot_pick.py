"""The aim helper of the real client (mc_shot.Client.pick, #2963), with a fake Gather."""
import mc_shot


def test_the_facing_point_is_1_62_below_the_eye_target():
    out = mc_shot.aims((10.0, 70.0, 20.0), dists=(3,))
    assert len(out) == 8
    for stand, face in out:
        assert face == (10.0, 70.0 - 1.62, 20.0) and stand[1] == 70.0 - 1.62
        assert max(abs(stand[0] - 10), abs(stand[2] - 20)) == 3


class FakeGather:
    def __init__(self, good):
        self.good, self.at, self.cmds = good, None, []

    def pos(self, u):
        return (10.0, 64.0, 20.0)

    def command(self, c):
        self.cmds.append(c)
        self.at = c.split()[2:5]

    def look(self, name):
        x, y, z = map(float, self.at)
        return (x, y + 1.62, z), (0, 0, 1)

    def pickable(self):
        return {"U"}

    def positions(self, uuids):
        return {}

    def target(self, eye, d, places):    # only the stand point good hits the unit; the others hit a building
        return ("unit", "U", set()) if round(eye[0], 2) == self.good else ("building", (0, 4, 0, 4), set())


def test_pick_clicks_only_the_side_that_hits_the_unit(monkeypatch):
    monkeypatch.setattr(mc_shot.time, "sleep", lambda s: None)
    c = object.__new__(mc_shot.Client)
    c.name, c.size, clicks = "aoe2mc", (1280, 720), []
    c.click = lambda x, y, button=1: clicks.append((x, y, button))
    g = FakeGather(good=13.0)
    stand = c.pick(g, "U")
    assert stand[0] == 13.0 and clicks == [(640, 360, 3)] and len(g.cmds) == 2
    assert "facing 10.00 63.38 20.00" in g.cmds[0]
    clicks.clear()
    assert c.pick(FakeGather(good=99.0), "U") is None and clicks == []
