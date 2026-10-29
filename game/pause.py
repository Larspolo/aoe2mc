"""Pause and continue the game (#3374): /tick freeze stops the mobs, Gather.run skips its steps and ticks."""
import json

import diplomacy


def toggle(g, player):
    """Pause the game of player 1, or continue it. On continue, t0 of the Gather and its bots moves by the paused
    real time, as diplomacy.faster does, so that recap.game_time does not jump."""
    g = diplomacy.main(g)
    now = g.clock()
    if getattr(g, "paused", False):
        for h in [g, *(b.g for b in g.bots)]:
            h.t0 += now - g.paused_at
        g.paused = False
        g.command("tick unfreeze")
        text = f"Player {player} continued the game."
    else:
        g.paused, g.paused_at = True, now
        g.command("tick freeze")
        text = f"Player {player} paused the game."
    g.command("tellraw @a " + json.dumps({"text": text, "color": "gold"}))
    return g.paused
