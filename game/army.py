"""The armies of a battle challenge (#3910, epic #3759): the keys "army" (the units of player 1) and "enemy" (the units
of player 2) of a line of game/data/challenges.jsonl, {AoE2 name: count}. They stand on any converted world: the army
in the middle of the map, the enemy GAP blocks north of it. The key "waves" (a list of enemy armies, #3906) sends each
wave when the wave before it is dead, and it attacks the army (ai.attack). The goal is complete when no enemy unit
lives; the medal comes from the units lost (score.fallen keeps them in g.losses).

    "check": "army.battle"   # game/data/challenges.jsonl
"""
import math

GAP = 48                                                               # blocks from the army to the enemy
SPACE = 2                                                              # blocks between two units


def cells(g, center, n):
    """n free cells near the block point center, SPACE blocks apart, the nearest first."""
    cx, cz = center
    r = SPACE * (math.isqrt(n) + 4)
    near = sorted(((x, z) for x in range(cx - r, cx + r + 1, SPACE) for z in range(cz - r, cz + r + 1, SPACE)
                   if g.map.free(x, z)), key=lambda c: ((c[0] - cx) ** 2 + (c[1] - cz) ** 2, c))
    return near[:n]


def place(g, units, center, player):
    """Summon units {name: count} of player near center (train.summon). Returns the UUIDs."""
    import train  # train imports gather, gather imports challenge
    names = [n for n, k in sorted(units.items()) for _ in range(k)]
    out = []
    for name, (x, z) in zip(names, cells(g, center, len(names))):
        if uuid := train.summon(g, name, (x + 0.5, float(g.map.y(x, z)), z + 0.5), player=player):
            out.append(uuid)
    return out


def wave(g, c, units):
    """Place the enemy units {name: count} north of the middle; a wave (#3906) attacks a live unit of the army."""
    import ai  # ai imports gather, gather imports challenge
    n = g.map.n // 2
    g.challenge_foes = place(g, units, (n, n - GAP // 2), 2)
    if (target := next(iter(g.positions(vars(g).get("challenge_army", ()))), None)) and "waves" in c:
        names = [n for n, k in sorted(units.items()) for _ in range(k)][:len(g.challenge_foes)]
        ai.attack(g, g.challenge_foes, names, g.map.T, target)


def battle(g, c):
    """The goal of a battle challenge: place both armies at the first call (the first wave of "waves"), then the next
    wave when all enemy units are dead; True when all enemy units of the last wave are dead."""
    waves = c.get("waves") or [c["enemy"]]
    if vars(g).get("challenge_foes") is None:
        n = g.map.n // 2
        g.challenge_army, g.challenge_wave = place(g, c["army"], (n, n + GAP // 2), g.player), 0
        wave(g, c, waves[0])
        return False
    if g.positions(g.challenge_foes):
        return False
    if vars(g).get("challenge_wave", 0) + 1 < len(waves):
        g.challenge_wave += 1
        wave(g, c, waves[g.challenge_wave])
        return False
    return True
