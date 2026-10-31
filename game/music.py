"""Calm music in peace (#5341, research: docs/research/music.md): each person hears the peace tracks of
game/data/music.jsonl one after the other. Each new track first stops the music source, so the own background music
of the client does not play over it. The lengths are real seconds: g.clock(), not the game speed."""
import table

TRACKS = table.load("music.jsonl")
PEACE = [r for r in TRACKS if r["use"] == "peace"]               # in file order: in turn, not at random


def tick(g):
    """Start the next peace track for each person whose last track ended. A bot (h.share) gets no command."""
    if g.ended or not PEACE or not hasattr(g, "clock"):                  # a test loop with no clock
        return
    import fog  # fog imports gather, gather imports this module
    now, state = g.clock(), vars(g).setdefault("music", {})
    for h in fog.gathers(g):
        if getattr(h, "share", None):
            continue
        n, end = state.get(h.player, (-1, None))
        if end is not None and now < end:
            continue
        n = (n + 1) % len(PEACE)
        state[h.player] = (n, now + PEACE[n]["seconds"])
        who = f"@a[team=p{h.player}]"
        g.command(f"stopsound {who} music")
        g.command(f"playsound {PEACE[n]['name']} music {who} ~ ~ ~ 1 1 1")


def stop(g):
    """Stop the music of all persons at the end of the game: the end tune plays alone."""
    g.command("stopsound @a music")
