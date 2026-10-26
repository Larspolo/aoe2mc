"""Check of #933: the score panel of the live replay at about 5:00 of samples/de-64.3.aoe2record (Paper, real client)."""
import json, shutil, sys, time
R = "/home/user/aoe2mc"
sys.path[:0] = [R, R + "/game", R + "/tools", R + "/tests"]
import combat, mc_shot, replay, replay_input  # noqa
from game import run  # noqa

S = sys.argv[1]
world = shutil.copytree(S + "/recW", S + "/recW_run")
data = json.load(open(world + "/aoe2mc.json"))


class Done(Exception):
    pass


with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    game.forceload()
    combat.setup(game, data)
    inp = replay_input.Input(game)
    inp.setup()
    state = {"t0": None, "shots": 0}

    def poll(control):
        inp(control)
        if state["t0"] is None:
            control["jump"] = 300_000                   # the jump of the replay control (#687) to 5:00
            state["t0"] = time.monotonic()
        elif control.get("time", 0) >= 310_000 and time.monotonic() - state["t0"] > 20:
            time.sleep(3)                               # one census after the jump
            print("sidebar:", game.command("scoreboard players list"), flush=True)
            client.shot(f"{S}/score_{state['shots']}.png")
            state["shots"] += 1
            if state["shots"] == 2:
                raise Done
            game.command("tp aoe2mc ~ ~ ~ ~90 ~")
    try:
        replay.Replay(game, data, game.version, ai=True).run(2.0, 0, bar=True, poll=poll, log=None)
    except Done:
        pass
    for p in (1, 2):
        print("player", p, game.command(f"team list p{p}")[:200], flush=True)
