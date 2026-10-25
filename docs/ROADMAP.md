# Roadmap

The tickets are GitHub Issues. Their labels give the order of work (see `docs/STEERING.md`).
This file gives the phases and the reasons for the order. The agent updates it when a phase is complete
or when the owner changes the direction.

## Aim

- Every AoE2 object type has a recognizable form in Minecraft.
- The worlds load without errors in the newest Minecraft Java version.
- The known limits in the README are solved, or the README explains them.

## Principles

1. Easy tickets first. They make the work cycle and the tools better at low risk.
2. A safety net before a refactor: the golden test (#4) comes before the cleanups.
3. Tools before design work: the agent must see a design (#11) before it makes new designs.
4. One ticket = one PR. Large tickets are split first.
5. The owner decides the priorities. The agent proposes changes.

## Phases

### 1. Safety net and quick fixes
#2 lint errors · #3 `convert()` more than once · #4 golden test · #5 road pass bug · #6 dead branches ·
#7 option checks · #8 unknown object IDs · #9 world icon · #10 coverage report

### 2. Tools to see and test the output
#11 isometric render tool · #12 Mojang hosts (owner) · #13 headless Minecraft server check · #18 test maps

### 3. Minecraft 26.3
#14 (split into sub-issues: research, data, version option, entity format, new default)

### 4. Correctness and known limits
#15 large chunks · #16 spawn at player 1 · #17 README · #19 waterlogged blocks · #20 unit facing ·
#21 garrisoned units · #23 map orientation

### 5. Designs and features
#22 unique buildings · #25 diagonal gates · #24 packaging · #26 speed · #27 scenario book · #28 birds ·
#29 sample maps (owner)

## Later ideas (no ticket yet)

- Real map tests with the sample maps of #29.
- A small datapack with the scenario name, the player colors as teams, and the triggers as text.
