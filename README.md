# aoe2mc

Converts an Age of Empires II: Definitive Edition scenario (`.aoe2scenario`) into a Minecraft Java Edition world.

## Files

| File | Description |
|---|---|
| `aoe2mc.py` | The converter (terrain, trees, resources, world writer) |
| `buildings.py` | The building designs (must be in the same folder as `aoe2mc.py`) |
| `units.py` | The unit mapping (must be in the same folder as `aoe2mc.py`) |
| `samples/stress.aoe2scenario` | Test map: units against every side of buildings, trees, mines, cliffs and a mountain, on slopes and on a bridge |
| `samples/unit_gallery.aoe2scenario` | Test map with every unit type |
| `samples/gallery.aoe2scenario` | Test map: every building type, 8 civilizations |
| `samples/test_village.aoe2scenario` | Small test map with terrain, water and a hill |
| `tools/` | Tools for tests and debugging: test scenarios, world reader, 3D render, coverage report, Minecraft data and server check |
| `tests/` | The tests (pytest) |
| `docs/` | Design guide, roadmap, steering, coverage report and other notes |

The repository has no converted worlds. Convert a sample map to get one (see "Use").

## Install

Two ways:

- Install the command `aoe2mc`: `pip install .` in the repository folder, or
  `pipx install git+https://github.com/Larspolo/aoe2mc`.
- Run the script from the repository folder: `pip install -r requirements.txt`, then use `python aoe2mc.py`.

## Use

    aoe2mc MyMap.aoe2scenario MyMapWorld --preview
    python aoe2mc.py MyMap.aoe2scenario MyMapWorld --preview      (the same, from the repository folder)

Copy the folder `MyMapWorld` into your Minecraft `saves` folder. Open it in Minecraft Java 1.21.1 or newer.
The world is in creative mode. Outside the map there is only void. The world list shows a small top view of the map
(`icon.png`).

| Option | Default | Description |
|---|---|---|
| `--tile-size` | 4 | Blocks per AoE2 tile, in each direction. 5 or 6 gives more detail. Range 1–16. |
| `--level-height` | 3 | Blocks per AoE2 elevation level. Range 1–16. |
| `--architecture` | from civ | One architecture set for all players |
| `--player-architecture` | – | Architecture set for one player, for example `6=western`. Can be repeated. |
| `--name` | file name | World name in the Minecraft menu |
| `--seed` | 1 | Seed for random details (tree heights, flowers) |
| `--preview` | off | Writes `preview.png` (top view) into the world folder |
| `--mc-version` | 1.21.1 | Minecraft Java version of the output: `1.21.1` or `26.3`. The 26.3 output is not complete yet. |
| `--no-units` | off | Do not convert units |
| `--no-barriers` | off | Do not fill building footprints with invisible barrier blocks |
| `--spawn X,Z` | start view or town center of player 1 | Player spawn in tiles. Without it the spawn is the start view of player 1, else the front of its first town center, else the map center. |
| `--orientation` | `ne` | Minecraft corner of the top corner of the AoE2 screen: `ne`, `se`, `sw` or `nw`. The map, the buildings, the units and the spawn view turn with it. |

## Buildings

Each building fills its AoE2 footprint. The front (main door) is on the south side, as in the AoE2 camera view.
The program reads the player color and civilization from the scenario. Each civilization uses one of 9 architecture sets:

| Set | Civilizations | Wonder |
|---|---|---|
| western | Britons, Franks, Celts, Burgundians, Sicilians, Saxons | Gothic cathedral |
| central | Goths, Teutons, Vikings, Huns, Slavs, Magyars, Bulgarians, Lithuanians, Poles, Bohemians, Varangians, Danes | Gothic cathedral |
| mediterranean | Byzantines, Spanish, Italians, Portuguese, Romans, Armenians, Georgians, Greek civs | Gothic cathedral |
| middle_eastern | Persians, Saracens, Turks, Berbers, Achaemenids, Tatars, Cumans | Mosque |
| south_asian | Hindustanis, Dravidians, Bengalis, Gurjaras, Puru | Mosque |
| african | Ethiopians, Malians | Mosque |
| east_asian | Japanese, Chinese, Koreans, Mongols, Shu, Wu, Wei, Jurchens, Khitans | Pagoda |
| southeast_asian | Khmer, Malay, Burmese, Vietnamese | Angkor temple |
| mesoamerican | Aztecs, Mayans, Incas, Muisca, Mapuche, Tupi | Stepped pyramid |

Other supported objects: bridges, aqueducts, army tents, pavilions, yurts, huts, the amphitheatre, monuments,
landmark cathedrals, mountains, quarries, graves, ruins and shipwrecks.

## Units

All units stand still (no AI), do not despawn and are silent. Each unit has a name tag with its AoE2 name in the player color.
The world difficulty is Easy: on Peaceful, Minecraft removes the hostile mobs (the soldiers).

| AoE2 | Minecraft |
|---|---|
| Villagers | Villager with a matching profession |
| Monks, missionaries, priests | Evoker |
| Infantry | Zombie with sword or axe; spear units with trident |
| Archers / crossbow units | Skeleton with bow / crossbow |
| Skirmishers and other throwers | Drowned with trident |
| Gunpowder infantry | Pillager |
| Cavalry | Zombie on a horse with horse armor |
| Mounted archers | Skeleton on a skeleton horse |
| Camel units / elephants | Camel / ravager with a rider |
| Siege weapons | Minecart with a crew (zombie for rams, vindicator for mangonels and trebuchets, skeleton for scorpions, pillager for gunpowder) |
| Ships | Boat; crew and wood show the type (villager = fishing, blaze = fire ship, creeper = demolition ship, pillager = cannon ship, skeletons = warships) |
| King, queen | Zombie with a gold helmet |
| Trade carts | Donkey with a chest |
| Animals | Sheep, cow, pig, wolf, horse, llama, goat, chicken, fox, camel; boars, rhinos, crocodiles and bears are hoglins; small exotic animals are sheep |
| Fish (resources) | Cod, salmon, tropical fish |
| Relics | Decorated pot |

Armor shows the upgrade step: leather helmet, chainmail, iron, diamond. Unique units have gold armor, elite unique units netherite.
Helmets are unbreakable, so zombies and skeletons do not burn in the sun.

## Details and variation

Each building gets a random seed from its position, so a map always converts the same way, but no two buildings are the same:
- Houses have four designs: cottage, front gable, two floors with an overhanging upper floor, and cottage with a woodshed.
  The chimney position changes.
- Plaster, roof material and timber change a little (for example white or ochre plaster, wood or slate roofs).
- Glass windows can get open shutters, a sill and flower pots.
- Free ground next to the walls gets barrels, hay, firewood, lanterns, beehives and other things.
- Walls are not made of one block: similar blocks are mixed in (for example cracked and mossy stone bricks,
  calcite in white plaster, other tiles in a roof). The main block stays the large majority, so each building
  stays recognizable. Stone buildings have corner stones, half-timbered buildings a stone base row.
- Every 4th wall tile has a banner in the player color.

## Architecture sets without timber framing

Middle Eastern, South Asian and African buildings have plaster walls with stone bands instead of half-timbering:
a base row, a cornice and pilasters in an accent color, a parapet of wall blocks on the flat roof, and
(depending on the set) a sloped overhang under the roof (South Asian chhajja), small domed kiosks on large roofs
(chhatri), and wooden beams that stick out of the walls (African mud architecture).

| Set | Walls | Accent | Domes |
|---|---|---|---|
| South Asian | beige sandstone | red sandstone | white quartz |
| Middle Eastern | beige sandstone | light blue tiles | light blue |
| African | terracotta (mud) | brown terracotta | terracotta |

## Ground

Grass, forest, dirt and sand get patches and plants that are only decoration: worn and mossy patches,
short and tall grass, flower fields (one kind of flower per field), pink petals, ferns, mushrooms, moss carpet
and dead bushes.
Dirt is steppe: coarse dirt with patches of dry grass. Cliffs join into continuous rock ridges (snow on top in snow areas).
Fences are low wooden fences that connect to each other.
Roads are a mix of cobblestone, andesite, stone, gravel, tuff and cracked stone, with worn patches in the middle,
rough edges and worn verges of dirt path beside the road.

## Barriers

Like in AoE2, units cannot walk into, through or over buildings: the free space of each footprint is filled with
invisible barrier blocks up to 1 block above the building. Gates and bridges stay open, and farms are not filled.
Trees, gold and stone mines, berry bushes, rocks, cliffs and mountains also block their tile (3 blocks high),
so you cannot walk through a forest.
Use `--no-barriers` to walk into the buildings.

## Footprints

Every building and object (tree, mine, cliff, rock, mountain) keeps its blocks inside its AoE2 footprint up to head height
(3 blocks above the ground of each column). Only roof edges, tower tops, sails and tree crowns above that may stick out.
Thus a unit can always stand directly next to an object. Units over water stand on a bridge or dock deck if there is one.
The converter reports "units in a block"; this number must be 0.

## Decorations

Statues, column statues, shrines, market stalls, wells, hay stacks, lumber and siege props, barrels, weapon racks,
targets, rugs, vases, flower beds, fern patches, hedges, grapevines, broken carts, bonfires, signs, gallows and
oysters have small designs. Roads mix several stones and get worn edges.
If a scenario puts a unit on a building or an obstacle (possible in the AoE2 editor), the unit moves to the nearest free place.

## Overlapping objects

Eye-candy scenarios often place buildings on top of each other. A building that lies for more than 80% under one
larger building is skipped (for example a wonder that is hidden under the Great Pyramid). Natural objects
(trees, rocks, cliffs, mountains, mines) place no blocks inside building footprints.

## Development

    python3 -m pip install -r requirements-dev.txt
    ruff check .
    python3 -m pytest              # fast tests
    python3 -m pytest -m slow      # slow tests

Read these files first:
- [`CLAUDE.md`](CLAUDE.md): commands, code map and the rules of the domain.
- [`docs/STEERING.md`](docs/STEERING.md): how the owner steers the work with GitHub issues.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): the plan.
- [`docs/DESIGN.md`](docs/DESIGN.md): the rules for building, object and unit designs.

## Known limits

- Object types that the parser does not know (new IDs) are skipped.
- Garrisoned units are not converted. Birds are not converted.
- The direction that units face is not checked in the game yet. See [`docs/facing.md`](docs/facing.md) for the check.
- In scenarios older than version 1.56 the architecture set field can be wrong, so the program uses the civilization.
- Unique buildings use the design of a similar building (for example krepost → small castle).
- Diagonal gates are drawn along a tile axis.
- Map tile (x, y) becomes block (x × tile-size, z = y × tile-size). AoE2 shows the map as a diamond with the top corner
  at the top of the screen. In Minecraft this corner is in the north-east: the map is the in-game view turned 45°
  clockwise, not mirrored. A turn of 45° is not possible on a block grid. At the spawn the player looks north-east,
  as the AoE2 camera does.
  Use `--orientation` to put the top corner in another corner, for example `nw`. The building fronts turn with the map:
  south for `ne`, west for `se`, north for `sw` and east for `nw`.
