"""A chat guide for an owner play test on a running `game/run.py --play` server (as game/watch.py for a replay).

    python3 play_guide.py GAME_PORT WORLD STEPS.json ANSWERS.json

Each step: {"name", "setup": [commands], "task", "ask"}. "{BARRACKS}" in a setup command is the target UUID of the
own barracks (combat.target_uuid). The guide waits for a player, then for each step runs the setup, says the task
and the question in the chat, and waits for one chat answer (cheat codes do not reach the chat).
Prints JOINED, ASK and ANSWER lines, then DONE."""
import glob
import json
import os
import re
import sys
import time

sys.path[:0] = ["/Users/polo/aoe2mc/game", "/Users/polo/aoe2mc/tools"]
import combat  # noqa: E402
from rcon import Rcon  # noqa: E402

CACHE = "/Users/polo/aoe2mc/.cache"
CHAT = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> (.*)$")


def out(*a):
    print(*a, flush=True)


def server(port):
    """(folder, rcon port, password) of the server with game port `port`."""
    for d in sorted(glob.glob(CACHE + "/tmp*"), key=os.path.getmtime, reverse=True):
        p = os.path.join(d, "server.properties")
        if os.path.exists(p):
            props = dict(ln.strip().split("=", 1) for ln in open(p) if "=" in ln)
            if props.get("server-port") == str(port):
                return d, int(props["rcon.port"]), props["rcon.password"]
    sys.exit(f"no server with port {port}")


def main(port, world, steps_file, answers_file):
    folder, rport, password = server(port)
    r = Rcon("127.0.0.1", rport, password)
    log = os.path.join(folder, "logs", "latest.log")
    with open(os.path.join(world, "aoe2mc.json")) as f:
        objs = json.load(f)["objects"]
    barracks = next(combat.target_uuid(o["footprint"]) for o in objs if o["name"] == "BARRACKS" and o["player"] == 1)
    names = {"{BARRACKS}": barracks}
    for n in (1, 2):                                                    # the first militia of each player
        names[f"{{MILITIA{n}}}"] = next(o["uuid"] for o in objs if o["name"] == "MILITIA" and o["player"] == n)
    with open(steps_file) as f:
        steps = json.load(f)

    def say(msg, color="gold"):
        r.command(f"tellraw @a {json.dumps([{'text': '[check] ', 'color': 'aqua'}, {'text': msg, 'color': color}])}")

    def players():
        return [p.strip() for p in r.command("list").split(":", 1)[-1].split(",") if p.strip()]

    seen = [0]

    def chat():
        with open(log, errors="replace") as f:
            lines = f.read().splitlines()
        new, seen[0] = lines[seen[0]:], len(lines)
        return [m.groups() for ln in new if (m := CHAT.search(ln))]

    while not players():
        time.sleep(1)
    out(f"JOINED {players()}")
    time.sleep(8)                                                       # the chunks load
    chat()
    answers = []
    for k, s in enumerate(steps, 1):
        for c in s.get("setup", []):
            for key, v in names.items():
                c = c.replace(key, v)
            out(f"SETUP {c} -> {r.command(c).strip()[:120]}")
        say(f"Step {k} of {len(steps)}: {s['task']}")
        say(s["ask"], "yellow")
        say("When you are done, type your answer in the chat: ok, or what is wrong.", "gray")
        out(f"ASK {s['name']}")
        chat()
        while not (got := chat()):
            time.sleep(0.5)
        who, text = got[0]
        answers.append({"step": s["name"], "player": who, "text": text})
        out(f"ANSWER {s['name']}: <{who}> {text}")
        with open(answers_file, "w") as f:
            json.dump(answers, f, indent=1)
        say("Thank you." + (" Next step in 3 seconds." if k < len(steps) else " This part is done."), "green")
        time.sleep(3)
    out(f"DONE {len(answers)} answers")


if __name__ == "__main__":
    main(int(sys.argv[1]), *sys.argv[2:5])
