"""A guided owner check of a live replay (#718): play to a few seconds before each moment, pause, wait for the owner,
teleport the owner to the place, play, pause and ask in the chat, then go to the next moment.
Usage: .venv/bin/python out/watch718/watch.py WORLD OUT.json [--speed 4]
Prints READY / JOINED / ANSWER / DONE lines (flushed) for the agent that guides the owner."""
import json
import math
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import replay  # noqa: E402
import replay_input  # noqa: E402
import run  # noqa: E402

CHAT = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> (.*)$")
LEAD = 5                    # real seconds of play before the moment
WATCH = 30                  # real seconds of play after the moment, then the question


def say(game, msg, color="gold"):
    game.command(f"tellraw @a {json.dumps([{'text': '[check] ', 'color': 'aqua'}, {'text': msg, 'color': color}])}")


def out(*a):
    print(*a, flush=True)


def players(game):
    return [p.strip() for p in game.command("list").split(":", 1)[-1].split(",") if p.strip()]


class Stop(Exception):
    pass


class Guide:
    """poll(control) of Replay.run: the stages of the check, next to the hotbar input of the replay."""

    def __init__(self, game, stages, speed, answers):
        self.game, self.stages, self.speed, self.answers = game, stages, speed, answers
        self.input, self.k, self.state, self.t, self.r = replay_input.Input(game), 0, "play", 0.0, None
        self.server, self.seen = None, 0

    def chat(self):
        """The new chat lines of players since the last call: [(name, text)]. A restart (#979) gives a new log."""
        s = self.game.server
        if s is not self.server:
            self.server, self.seen = s, len(s.log)
        new, self.seen = s.log[self.seen:], len(s.log)
        return [m.groups() for ln in new if (m := CHAT.search(ln))]

    def place(self, stage):
        """Teleport the players next to the place of the stage: a villager that chops wood near a town center."""
        if stage.get("where") != "chopper" or not self.r:
            return
        r, g = self.r, self.game
        tcs = [((x0 + x1) / 2, (z0 + z1) / 2) for _, _, n, (x0, x1, z0, z1) in r.starts if "TOWN_CENTER" in n]
        best = None
        for i in r.working:
            v = r.units.get(i)
            if v is None or v.res != "wood" or (r.map and v.tree in r.map.farms):
                continue
            d, tc = min(((math.dist((v.pos[0], v.pos[2]), c), c) for c in tcs), default=(math.inf, None))
            if best is None or d < best[0]:
                best = (d, tc, v)
        if best is None:
            say(g, "No villager chops wood now: look around yourself.", "red")
            return
        d, tc, v = best
        m = re.findall(r"-?\d+(?:\.\d+)?", g.command(f"data get entity {v.uuid} Pos").rsplit(":", 1)[-1])
        x, y, z = map(float, m[:3]) if len(m) >= 3 else v.pos
        ux, uz = ((tc[0] - x) / (d or 1), (tc[1] - z) / (d or 1)) if tc else (0.7, 0.7)
        px, pz = x + 6 * ux, z + 6 * uz                             # on the side of the town center: open ground
        g.command(f"tag @a add {replay.VIEWER}")                    # else overview(join=True) moves them up high
        g.command("gamemode creative @a")
        for p in players(g):
            g.command(f"tp {p} {px:.1f} {y + 3:.1f} {pz:.1f} facing entity {v.uuid} eyes")
        g.command(f"effect give {v.uuid} glowing 20 0 true")       # the owner finds it at once
        out(f"PLACE villager {v.uuid} of player {v.player} at {x:.0f} {y:.0f} {z:.0f}, {d:.0f} blocks from a town center")

    def ask(self, stage):
        say(self.game, stage["ask"])
        say(self.game, "Type your answer in the chat: ok, or what is wrong. Type 'more' to see it longer.", "yellow")
        out(f"ASK {stage['name']}")

    def __call__(self, control):
        self.input(control)
        if self.k >= len(self.stages):
            return
        stage, now, real = self.stages[self.k], control.get("time", 0), time.monotonic()
        at = stage.get("at")
        if self.state == "play":
            if at is None:                                          # a stage that the owner does (the jumps)
                say(self.game, stage["task"])
                self.ask(stage)
                self.state = "answer"
            elif (at - LEAD * 1000 * self.speed - now) / 1000 / self.speed > 120:   # more than 2 real minutes: jump
                control["jump"] = at - LEAD * 1000 * self.speed
            elif now >= at - LEAD * 1000 * self.speed:
                control["paused"] = True
                self.state = "join"
                out(f"READY {stage['name']} at {now / 1000:.0f} s, players: {players(self.game)}")
                say(self.game, f"Paused {LEAD} s before {stage['what']}.")
        elif self.state == "join":
            if players(self.game):
                if self.t == 0:
                    self.t = real + (8 if self.k == 0 else 2)       # the first join: let the chunks load
                    out(f"JOINED {players(self.game)}")
                elif real >= self.t:
                    self.place(stage)
                    say(self.game, f"Look: {stage['what']}. It plays in 3 seconds.")
                    self.t, self.state = real + 3, "count"
        elif self.state == "count" and real >= self.t:
            control["paused"], control["speed"] = False, stage.get("speed", self.speed)   # watch at speed 1
            self.t, self.state = real + LEAD + WATCH, "watch"
        elif self.state == "watch" and real >= self.t:
            control["paused"] = True
            self.ask(stage)
            self.state = "answer"
        elif self.state == "answer":
            for who, text in self.chat():
                if text.strip().lower() == "more" and at is not None:
                    control["paused"] = False
                    self.t, self.state = time.monotonic() + WATCH, "watch"
                    return
                self.answers.append({"stage": stage["name"], "player": who, "time": round(now / 1000), "text": text})
                out(f"ANSWER {stage['name']}: <{who}> {text}")
                say(self.game, "Thank you. The replay continues to the next point.", "green")
                self.k, self.state, self.t = self.k + 1, "play", 0.0
                control["paused"], control["speed"] = False, self.speed
                if self.k == len(self.stages):                      # the last answer before the end: stop
                    raise Stop
                return
        if self.state != "answer":
            self.chat()                                             # only answers after a question count


def main():
    world, path = sys.argv[1], sys.argv[2]
    speed = float(sys.argv[sys.argv.index("--speed") + 1]) if "--speed" in sys.argv else 4.0
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    end = max(e["time"] for e in data["timeline"])
    t = replay.aoe2mc.game_time
    stages = [
        {"name": "chop", "at": t("3:00"), "where": "chopper", "speed": 1.0, "what": "a villager that chops a tree "
         "(it glows), at speed 1", "ask": "1. Do the walk, the turn to the tree, the particles and the sound look and "
         "feel right?"},
        {"name": "jumps", "task": "2. Now use the jumps: right click the ender pearl (1 minute forward), then open the "
         "menu and click a jump. Look at the 'Jump to ...' text while it waits.",
         "ask": "2. Is the wait with 'Jump to ...' acceptable?"},
        {"name": "end", "at": end, "what": f"the end of the replay at {end // 60000}:{end // 1000 % 60:02d}",
         "ask": "3. Is the end clear?"},
    ]
    if "--only" in sys.argv:                                        # a second try of some stages
        only = sys.argv[sys.argv.index("--only") + 1].split(",")
        stages = [s for s in stages if s["name"] in only]
    answers = []
    with run.Game(world) as game:
        guide = Guide(game, stages, speed, answers)

        def setup():
            game.forceload()
            import combat
            combat.setup(game, data)
            guide.input.setup()
        setup()
        saved = run.save(game)

        def restart():
            out("RESTART (a jump back): the owner must join again")
            game.stop()
            run.restore(saved, game.world)
            game.start()
            setup()

        def make():
            guide.r = replay.Replay(game, data, game.version, ai=True)
            return guide.r
        out(f"SERVER localhost:{game.game_port}")
        try:
            stats = replay.live(make, speed, 0, restart, bar=True, poll=guide, log=None)
        except Stop:
            stats = {"stopped after": stages[-1]["name"]}
            time.sleep(5)
        finally:
            shutil.rmtree(saved, ignore_errors=True)
        out(f"STATS {stats}")
        last = stages[-1]
        if guide.k < len(stages):                                   # the end stage: the replay is over now
            guide.k = len(stages) - 1
            time.sleep(4)
            guide.ask(last)
            guide.chat()
            got = []
            while not got:
                got = guide.chat()
                time.sleep(0.5)
            who, text = got[0]
            answers.append({"stage": last["name"], "player": who, "time": round(end / 1000), "text": text})
            out(f"ANSWER {last['name']}: <{who}> {text}")
            say(game, "Thank you. The check is done. The server stops in 10 seconds.", "green")
            time.sleep(10)
        errors = [ln for ln in game.server.log if re.search(r"ERROR|Exception", ln) and "minecraftservices" not in ln]
    with open(path, "w") as f:
        json.dump({"answers": answers, "stats": stats, "errors": errors[:30]}, f, indent=1, default=str)
    out(f"DONE {len(answers)} answers, {len(errors)} error lines")


if __name__ == "__main__":
    main()
