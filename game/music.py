"""Calm music in peace (#5341, research: docs/research/music.md): each person hears the peace tracks of
game/data/music.jsonl one after the other. Each new track first stops the music source, so the own background music
of the client does not play over it. The lengths are real seconds: g.clock(), not the game speed.
Battle music (#5342): when an enemy hits a unit or a building of a player, its people hear the battle tracks until no
own unit took a hit for the "calm" seconds of the battle track. The signal: the plugin hook of the attack alerts
(Alerts.hit, the same enemy filter), read with one `aoe hits` per second for all teams. Vanilla has no hit event of a
mob (the damage_taken statistic counts players only; HurtTime and the tag aoe2mc.hit last 10 ticks only)."""
import re

import table

TRACKS = table.load("music.jsonl")
PEACE = [r for r in TRACKS if r["use"] == "peace"]               # in file order: in turn, not at random
BATTLE = [r for r in TRACKS if r["use"] == "battle"]
READ = 1.0                                                       # real seconds between two reads of the hits


def hits(g):
    """The players with an enemy hit on an own unit or building since the last call (the plugin, `aoe hits`). No
    plugin (a vanilla server): no hits, only the peace tracks."""
    if not getattr(g, "paper", False):
        return set()
    m = re.search(r"Hits:(.*)", g.command("aoe hits") or "")
    return {int(t[1:]) for t in m[1].split() if re.fullmatch(r"p\d+", t)} if m else set()


def tick(g):
    """Start the next track for each person whose last track ended, or a track of the other kind when the fight
    starts or ends: no command between. A bot (h.share) gets no command."""
    if g.ended or not PEACE or not hasattr(g, "clock"):                  # a test loop with no clock
        return
    import fog  # fog imports gather, gather imports this module
    now, state = g.clock(), vars(g).setdefault("music", {})
    if BATTLE and now >= state.get("read", now):
        state["read"] = now + READ
        for p in hits(g):
            state.setdefault(p, {})["hit"] = now
    for h in fog.gathers(g):
        if getattr(h, "share", None):
            continue
        s = state.setdefault(h.player, {})
        use, end = s.get("use"), s.get("end")
        fight = use == "battle" and now < s.get("hit", now) + BATTLE[s["battle"]]["calm"]
        want = "battle" if fight or BATTLE and s.get("hit") is not None and use != "battle" else "peace"
        if want == use and end is not None and now < end:
            continue
        if want == "peace":
            s.pop("hit", None)                                          # a hit before the calm starts no new fight
        tracks = BATTLE if want == "battle" else PEACE
        n = s[want] = (s.get(want, -1) + 1) % len(tracks)
        s["use"], s["end"] = want, now + tracks[n]["seconds"]
        who = f"@a[team=p{h.player}]"
        g.command(f"stopsound {who} music")
        g.command(f"playsound {tracks[n]['name']} music {who} ~ ~ ~ 1 1 1")


def stop(g):
    """Stop the music of all persons at the end of the game: the end tune plays alone."""
    g.command("stopsound @a music")
