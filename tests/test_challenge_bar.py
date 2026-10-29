import json

from game import challenge


class Fake:
    def __init__(self):
        self.sent = []

    def command(self, cmd):
        self.sent.append(cmd)


def test_boss_bar_is_short_and_the_goal_is_in_the_chat():
    for name, c in sorted(challenge.CHALLENGES.items()):
        g = Fake()
        challenge.show(g, c, 0)
        bar = json.loads(next(x for x in g.sent if x.startswith(f"bossbar set {challenge.BAR} name ")).split(" name ", 1)[1])
        assert len(bar) <= 60, (name, bar)                         # a 1280 px screen cut the long goal (#4092)
        assert any(x.startswith("tellraw @a ") and json.dumps(c["goal"]) in x for x in g.sent), name
