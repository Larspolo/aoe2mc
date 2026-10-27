"""The play guide runs the cheat codes of a step for the owner (game/play_guide.py, key "cheats", #2052)."""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import cheats  # noqa: E402
import play_guide  # noqa: E402


class Server:
    """A fake server with one player: the game (cheats.clicks) does a code one poll after its score is set, as
    gather.Gather.clicks; with game=False no game reads the scores (no --cheats)."""

    def __init__(self, log, game=True):
        self.now, self.sent, self.score, self.done, self.game, self.log = 0.0, [], None, [], game, log
        self.asked = False
        log.write_text("[11:59:00 INFO]: Done (3.0s)!\n")

    def command(self, cmd):
        self.sent.append(cmd)
        self.asked |= cmd.startswith("tellraw") and "type your answer" in cmd
        if cmd == "list":
            return "There are 1 of a max of 20 players online: Lars"
        if m := re.fullmatch(rf"scoreboard players set Lars {cheats.OBJECTIVE} (\d+)", cmd):
            self.score = int(m.group(1))
        if cmd == f"scoreboard players get Lars {cheats.OBJECTIVE}":
            if self.score is None:
                return f"Can't get value of {cheats.OBJECTIVE} for Lars; none is set"
            reply = f"Lars has {self.score} [Cheat]"
            if self.game:
                self.done.append(cheats.NAMES[self.score - 1])
                self.score = None
            return reply
        return "ok"

    def clock(self):
        return self.now

    def sleep(self, s):
        self.now += s
        if self.asked:                                                  # the owner answers after the question
            self.asked = False
            with open(self.log, "a") as f:
                f.write("[12:00:00 INFO]: <Lars> ok\n")


STEPS = [{"name": "1138-wonder", "setup": ["say hi"], "cheats": ["aegis", "robin hood"], "task": "Build a wonder.",
          "ask": "Does the bar show?"}]


def run(tmp_path, game=True, steps=STEPS):
    s, lines = Server(tmp_path / "latest.log", game), []
    g = play_guide.Guide(s.command, str(tmp_path / "latest.log"), steps, {}, clock=s.clock, sleep=s.sleep,
                         say_log=lambda *a: lines.append(" ".join(map(str, a))))
    list(g.run())
    return s, lines


def test_a_step_runs_its_cheat_codes_in_order_after_the_setup(tmp_path):
    s, lines = run(tmp_path)
    assert s.done == ["aegis", "robin hood"]                              # one code per score: in order
    sets = [c for c in s.sent if c.startswith("scoreboard players set")]
    assert sets == [f"scoreboard players set Lars {cheats.OBJECTIVE} {cheats.NAMES.index(c) + 1}"
                    for c in ("aegis", "robin hood")]
    assert s.sent.index("say hi") < s.sent.index(sets[0])               # after the setup, before the task
    assert s.sent.index(sets[1]) < min(i for i, c in enumerate(s.sent) if c.startswith("tellraw"))
    assert "CHEAT aegis -> done" in lines and "CHEAT robin hood -> done" in lines


def test_a_code_that_the_game_does_not_do_is_reported_and_the_guide_continues(tmp_path):
    s, lines = run(tmp_path, game=False)
    assert any(ln.startswith("CHEAT aegis -> not done") and "--cheats" in ln for ln in lines)
    assert lines[-1] == "DONE 1 answers"


def test_an_unknown_code_stops_the_guide_before_the_first_step(tmp_path):
    with pytest.raises(ValueError, match="robin hod"):
        run(tmp_path, steps=[dict(STEPS[0], cheats=["aegis", "robin hod"])])
