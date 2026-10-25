# Example maps

Small AoE2 DE scenarios that show what aoe2mc can do. Code in `tools/scenarios.py` makes them, so there is no
license problem. A test (`tests/test_examples.py`) makes sure that the code gives the committed file again.

| Map | What it shows |
|---|---|
| `river_town.aoe2scenario` | 64 × 64 tiles, Britons. A town with stone walls and two gates, a town center, a market, a mill with farms, houses, a blacksmith and a barracks. A river with a bridge, a dock and ships. A castle on a hill, a forest with a lumber camp, gold and stone mines, sheep, deer, a boar and villagers at work. |

## Convert a map

    python3 aoe2mc.py examples/river_town.aoe2scenario RiverTown --preview

Copy the folder `RiverTown` into the `saves` folder of Minecraft Java.

## Make a map again

    python3 tools/scenarios.py river_town examples/river_town.aoe2scenario

After a change to the maker, commit the new file.
