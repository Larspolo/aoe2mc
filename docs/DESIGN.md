# Design guide

These rules apply to all design work: buildings, objects, units and animals.
The owner set them on 2026-10-25 (#40):

> I want all the buildings to look as close to in-game as possible while also keeping it making sense. So if there
> should be a door, use a door, for a target use the target block, etc. Also some noise should still exist so it
> doesn't look so plain.

The `design` skill (`.claude/skills/design/SKILL.md`) gives the steps of one design ticket.

## 0. Minecraft features first

The owner added this rule on 2026-10-26:

> I would rather use the MC pathfinding. In general I want to use MC features where possible. For example the
> stacking on top of each other in the boat or even just the boat in general, or how I wanted to map the animals
> based on their aggressiveness.

It is rule 2 ("real blocks for real things") for behavior. Use the feature of Minecraft that does the job, before
you write own logic:

| Job | Minecraft feature | Not this |
|---|---|---|
| A unit walks to a place or to an enemy | Mob AI and path finding (vanilla goals; in the game program a Paper plugin for "walk to a point") | own path finding with `/tp` steps |
| Units in a ship, riders, garrisons | `Passengers` (riders, stacks of riders), boats and chest boats | units next to the ship, or none |
| Animal behavior | the behavior class of the mob (passive, neutral, hostile, `docs/animals.md`) | own anger rules |
| Hit points, attack, speed, armor | entity attributes (`max_health`, `attack_damage`, `movement_speed`, `armor`) and vanilla damage | own hit point counters |
| Teams and player colors | scoreboard teams | a tag per unit only |
| Doors, gates, light, water | block states and block entities (`open`, `lit`, `waterlogged`) | look-alike blocks |

Write own logic only when Minecraft has no feature for the job, or when the feature cannot give the AoE2 rule (for
example the AoE2 attack bonuses), and say why in the PR. Converted worlds stay vanilla: they must load in single player.

## 1. Like the game

- Copy the shape, the proportions, the colors and the main features of the in-game model.
- Use the model of the architecture set of the player (`Style` in `ARCH`, `CIV_ARCH`). A Western European castle
  and an East Asian castle are different designs.
- Use a reference image of the game (see the `design` skill). Do not design from memory when an image is available.
- Keep the footprint of the AoE2 object (`FOOTPRINT`). Use the height for size: a castle is higher than a house.
- When the game and Minecraft do not agree, keep the outline that a player knows from a distance:
  roof shape, towers, domes and the main colors.

## 2. Real blocks for real things

A thing in the model is the Minecraft block of that thing. Do not paint it with a block that has a similar color.

| AoE2 feature | Minecraft block | Used today in |
|---|---|---|
| Door, main entrance | `*_door` (front: south side), or an open arch for large gates | `tomb`, `house`, `granary`, `wooden_fort` +25 more |
| Window | `glass_pane`; `iron_bars` for fortified buildings | `barracks`, `ring`, `archery_range`, `donjon` +18 more |
| Archery target | `target` | `archery_range` |
| Bow and arrow work | `fletching_table` | `archery_range` |
| Forge, smithy | `blast_furnace`, `anvil`, `smithing_table`, `cauldron` (water) | `blacksmith` |
| Forge hearth, quench tub (inside) | `lava_cauldron` beside the chimney, `water_cauldron[level=3]` | `blacksmith`, `pasture`, `stable`, `caravanserai` |
| Fire, cooking | `campfire`, `smoker` | `decorate`, `burned_building`, `outpost`, `blacksmith` +3 more |
| Weapon rack, sharpening | `grindstone` | `mill_room`, `decorate`, `keep_inside`, `mining_camp` +4 more |
| Training dummy | `oak_fence`, `hay_block`, `carved_pumpkin` | `barracks`, `pasture`, `settlement`, `decorate` +10 more |
| Bell | `bell` | `town_center`, `fortified_church`, `monastery` |
| Bed (inside) | `*_bed` (player color), head to the north | `furnish`, `barracks` |
| Hearth in a hut or yurt | lit `campfire` in the middle (the smoke goes through the roof), `*_carpet` rugs around it | |
| Bedroll in a tent | `*_bed` (player color) on the floor along the canvas | |
| Spears in a rack | `lightning_rod` | |
| Map table of a commander | `cartography_table` | |
| Cushion | `red_wool` next to a low `*_slab[type=top]` table | |
| Table with a light (inside) | `*_slab[type=top]` with a `lantern` on it, a `*_stairs` stool | `furnish`, `town_hall`, `pagoda`, `blacksmith` +26 more |
| Storage (inside) | `chest` at the back wall | `furnish`, `town_hall`, `decorate`, `keep_inside` +16 more |
| Rug | `*_carpet` | `furnish_worship`, `town_hall`, `keep_inside`, `cart` +1 more |
| Throne (inside) | `*_stairs` (backrest north) between `gold_block`s, `*_wall_banner`s (player color) over it | `throne_hall` |
| Treasure (inside) | `chest` and `gold_block` in the back corners | `throne_hall` |
| Statue in a hall (inside) | `chiseled_stone_bricks` base, `waxed_copper_block` and `waxed_cut_copper` (bronze) or `quartz_pillar` and `gold_block` (marble), lit `candle`s at its sides | |
| Tomb (inside) | `smooth_quartz` cenotaph with a `green_carpet` cloth on a `red_carpet`, lit `candle`s around it | |
| Arena (inside) | `sand` floor, seats that step down to it, a gate passage from the south, cells under the seats behind `iron_bars` with `hay_block`, `*_wall_banner`s and a `smooth_quartz_stairs` seat at the box of the emperor | |
| Theatre stage (inside) | `dark_oak_slab` stage, `*_wall_banner`s behind it, `potted_fern`, `flower_pot`, `lantern`s | |
| Oracle's tripod (inside) | `cauldron` before the statue of the god, `decorated_pot`s (gifts) in the corners | |
| Idol on an altar (inside) | `gold_block` on `chiseled_sandstone`, lit `candle`s at its sides, `potted_poppy` offerings | |
| Sanctum in a temple tower (inside) | `gold_block` idol on `chiseled_red_sandstone`, a path of `orange_carpet`, lit `candle`s, `potted_red_tulip` and `potted_orange_tulip` offerings | |
| Offering stone (outside) | `mossy_cobblestone` with a `skeleton_skull`, lit `candle`s, a `campfire` before it, skulls on carved posts | |
| Spiral stair in a tower (inside) | `*_stairs` around a 2 × 2 shaft, one step per block, a hanging `lantern` under every 6th step | |
| Bench (inside) | `*_stairs` in a row | `storage`, `shelter`, `furnish_worship`, `town_hall` +37 more |
| Sacred rock in a shrine (inside) | `stone`, `andesite` and `tuff` in a low mound, lit `candle`s around it, a ring of `quartz_pillar` columns | |
| Hay loft (inside) | `spruce_slab[type=top]` with `hay_block` on it | `settlement`, `cart`, `stable`, `market` +22 more |
| Light on a wall (inside) | `wall_torch` | `town_hall`, `archery_range`, `stable` |
| Loom, cloth | `loom`, wool | `decorate`, `command_tent`, `dock` |
| Market goods | `barrel`, `chest`, `composter`, `hay_block`, `melon`, `pumpkin` | `market`, `decorate`, `settlement`, `harbor` +10 more |
| Bales of trade goods (inside) | `*_wool` and `hay_block`, stacked in corners and along walls | |
| Counting room (inside) | `cartography_table` with a `lantern`, `lectern[has_book=true]` | |
| Market stall | lean-to of roof stairs on `*_fence` posts; wool awning in stripes for flat-roof sets | `pasture`, `nine_bands`, `fish_trap`, `outpost` +37 more |
| Upper floor (inside) | `*_planks` floor and a `ladder` | `outpost`, `tower`, `barracks`, `market` +32 more |
| Painted trim (deck edge, band) | `*_concrete` (player color) | `torii`, `stupa`, `pyramid`, `dock` +3 more |
| Relief panel, carving | `chiseled_stone_bricks` | `harbor`, `temple`, `aqueduct`, `furnish_worship` +6 more |
| Balustrade of a stair | `polished_granite` | `pyramid` |
| Stone bridge (#455) | `stone_bricks` piers with cutwaters every tile, `stone_brick_stairs[half=top]` vault, `stone_brick_wall` balustrade with `chiseled_stone_bricks` posts, `cracked_stone_bricks` on cracked and broken pieces | |
| Crop field | `wheat` rows (ages 5–7) on `farmland`, furrows of bare `farmland`, `dirt_path` edge | `folwark` |
| Hay, fodder | `hay_block` | `settlement`, `hut`, `mill_room`, `granary` +15 more |
| Log pile, cut timber | `*_log[axis=x]` stacked as a pyramid (`log_pile`) | `log_pile`, `barricade`, `wooden_bridge`, `fish_trap` +36 more |
| Debris heap of a barricade | `cobblestone`, `andesite`, `spruce_log`, `stripped_spruce_log`, `spruce_planks`, `spruce_slab`; on top `mangrove_roots` (branches), `spruce_fence`, `oak_leaves` (ivy), `barrel`, `decorated_pot` |  |
| Wooden bridge: boards across the bridge, posts over the deck | `stripped_spruce_log[axis=*]` and `spruce_planks` in turn, `stripped_oak_log` posts every second block, no railing |  |
| Hoist | a log post and arm, `chain`, a hanging log | `harbor_chain`, `hang`, `lumber_camp`, `shipyard` +3 more |
| Workbench | `crafting_table` | `lumber_camp`, `dock` |
| Millstone | `grindstone` | `mill_room`, `decorate`, `keep_inside`, `mining_camp` +4 more |
| Drive shaft of a windmill | `stripped_spruce_log[axis=y]` above the millstone | `mill_room`, `settlement`, `sapper_tunnel`, `shipyard` +15 more |
| Net loom, boat workbench | `loom`, `crafting_table`, `spruce_slab` | `dock` |
| Dried fish, ship timber | `dried_kelp_block`, `stripped_spruce_log` (stack on the quay) | |
| Light in a room or a yard | `lantern` on a barrel, or hanging under a beam | `hang`, `furnish`, `keep_inside`, `mill_room` +11 more |
| Ore, mined gold and stone | `gold_ore`, `raw_gold_block`, `cobblestone`, `stone`, `andesite` | `mining_camp`, `mole` |
| Mine cart track | `rail` | `mining_camp` |
| Water trough | `cauldron` (water) | `decorate` |
| Fountain | `water` source in a 3 × 3 rim of `stone_bricks` (`smooth_quartz` for antiquity), posts on the corners |  |
| Bench | three `*_stairs` in a row |  |
| Clay pots, amphorae, water pots | `decorated_pot`, `water_cauldron` |  |
| Banner, flag | `*_banner` (player color), `Canvas.flag` | `town_hall`, `keep_inside`, `torii`, `pasture` +59 more |
| Player color band (walls, gate towers) | `*_wool` (player color), one row | `pavilion`, `yurt`, `command_tent`, `army_tent` +19 more |
| Fence, pen | `*_fence` | `pasture`, `nine_bands`, `fish_trap`, `outpost` +37 more |
| Gate of a pen | `*_fence_gate` | `pasture`, `folwark` |
| Fish trap basket | `bamboo_fence` rods on half-round hoops of `dark_oak_wood` and `stripped_oak_wood` |  |
| Wheel | open `*_trapdoor` on the side | `cart`, `university`, `market`, `dock` +9 more |
| Siege engine in the making | `stripped_spruce_log` frame, `oak_fence` posts, a `stripped_oak_log` ram beam with an `iron_block` head | `siege_workshop` |
| Tent canvas | `white_wool`, a valance of wool in the player color | `command_tent`, `army_tent`, `pavilion`, `yurt` +4 more |
| Tent poles of a pavilion | `stripped_spruce_log[axis=y]` at the corners, up to the roof edge | |
| Lookout hut on stilts (outpost) | `*_log` stilts with `spruce_fence` braces, a `*_wool` band (player color) and `white_wool` cloth, a `white_wool` roof with a valance (player color) | |
| Yurt felt | `blue_wool` with a zig-zag of `white_wool` (or the inverse), a flat dome with a `spruce_trapdoor` crown ring | |
| Pavilion cloth | stripes of `*_wool` (player color) on `white_wool`, a `yellow_wool` valance, a white cone | |
| Thatch | `hay_block` | `settlement`, `hut`, `mill_room`, `granary` +15 more |
| Wicker wall of a hut | `mangrove_roots` between `spruce_log[axis=y]` posts | |
| Palisade stakes | `*_log[axis=y]` of two heights, `spruce_fence` tips | `barricade`, `fish_trap`, `outpost`, `wooden_fort` +39 more |
| Gold statue, finial | `gold_block` | `buddha_statue`, `dome_rock`, `ring`, `caravanserai` +15 more |
| Painted wood (torii) | `red_concrete`, black top beam | `torii` |
| Climbing plants | `vine`, `azalea_leaves` | `pillar`, `garden` |
| Charred timber | `coal_block`, `blackstone`, dark oak logs | `burned_building` |
| Scaffolding, building site | `scaffolding` posts, `spruce_slab` decks, `ladder` | `scaffolding`, `scaffold_walk` |
| Standing stones with lintels | `stone`, `andesite`, `tuff` posts, a ring of `stone` on top | `stonehenge` |
| Stone seats of a theatre | `stone_bricks` rising outward, `smooth_stone` and slabs on top | `theatre` |
| Spire tip, finial | `lightning_rod` | `nine_bands`, `storage`, `shrine`, `feitoria` +20 more |
| Copper roof, copper dome | `weathered_cut_copper`, `weathered_copper` | `cathedral` |
| Slate spire | `deepslate_tiles` | `hall_of_heroes`, `cathedral` |
| Pinnacle | the `accent_wall` of the style (`*_wall`) | `ring`, `garden`, `courtyard_walls`, `bridge` +23 more |
| Striped marble | rows of `polished_deepslate` in the main stone | `caravanserai`, `stone_head` |
| Mud-brick pinnacle | `mud_brick_wall` on a buttress | `garden`, `storage`, `sankore`, `djenne` +15 more |
| Glazed tile band, tile panel | `blue_terracotta`; `Style.dome` terracotta over arches | `minaret_of_jam`, `caravanserai`, `dome_rock`, `gol_gumbaz` +1 more |
| Chhatri (small domed kiosk) | `quartz_pillar` posts and a small dome | `oracles_temple`, `arch_of_constantine`, `taj`, `university` |
| Chain, rope | `chain` | `harbor_chain`, `hang`, `lumber_camp`, `shipyard` +3 more |
| Bartizan (corner turret) | stone, `smooth_quartz` cap, `lightning_rod` | `temple_of_heaven`, `taj`, `stupa`, `dome_rock` +24 more |
| Terracotta roof (Portuguese, Sicilian, Polish) | `brick` stairs | `oracles_temple`, `folwark`, `svan_tower`, `feitoria` +13 more |
| Portcullis, grille | `iron_bars` | `donjon`, `krepost`, `tower`, `castle` +3 more |
| Wooden hoarding | wood slab (top) or `spruce_planks` with a `*_fence` rail | `helepolis`, `outpost`, `shipyard`, `wooden_fort` +44 more |
| Coat of arms | `*_wall_banner` (player color) over the gate | `town_hall`, `keep_inside`, `torii`, `sapper_tunnel` +41 more |
| Lamp | `lantern` | `hang`, `furnish`, `keep_inside`, `mill_room` +11 more |
| Lamp inside a room | `lantern[hanging=true]` under a ceiling, or on a `chain` | `hang`, `lumber_camp`, `blacksmith`, `dock` +14 more |
| Cloth awning | `*_wool` in the player color | `pavilion`, `yurt`, `command_tent`, `army_tent` +19 more |
| Column | `quartz_pillar` | `oracles_temple`, `arch_of_constantine`, `taj`, `university` |
| Sacred tree | `oak_log`, `oak_leaves[persistent=true]` | `pagan_shrine`, `log_pile`, `decorate`, `settlement` +3 more |
| Hides | `brown_wool` | `yurt`, `helepolis`, `market` |
| Nomad hide tent | `brown_wool` dome and peak, an ornament band of `white_wool` and `orange_wool`, `red_carpet` rug | |
| Band in the player color | `*_wool` (player color) | `pavilion`, `yurt`, `command_tent`, `army_tent` +19 more |
| Outside stairs to an upper floor | `*_stairs` of the wood of the set | `storage`, `shelter`, `furnish_worship`, `town_hall` +37 more |
| Books, study | `bookshelf`, `lectern` (with a book) | `library`, `university`, `town_hall`, `keep_inside` +2 more |
| Desks, light inside | `enchanting_table`, `cartography_table`, `candle` (lit, on shelves and desks), `lantern` on a `chain` (`hang()`) | `study`, `hang`, `furnish_worship`, `lumber_camp` +3 more |
| Ledger and trade maps (inside) | `lectern` (with a book) and `cartography_table` on a counter of top slabs | `market`, `study`, `library`, `town_hall` +3 more |
| Scholar statue | `chiseled_stone_bricks` pedestal, `quartz_pillar`, `chiseled_quartz_block` | `university`, `oracles_temple`, `arch_of_constantine` |
| Posts of an open belfry | `stone_brick_wall` | `bridge`, `ring`, `temple`, `barracks` +3 more |
| Orange roof tiles (Krepost; Central European, Southeast Asian sets) | `red_sandstone` stairs and blocks | `storage`, `fortified_church`, `shelter`, `taj` +25 more |
| Stepped stone roof (Mesoamerican set) | `stone_brick` stairs (hip roof) | `shelter`, `storage`, `temple`, `hall_with_yard` +17 more |
| Thatch or shingle roof (East Asian set) | `spruce` stairs | `pagoda`, `tomb`, `furnish_worship`, `wooden_fort` +12 more |
| Cannon | `polished_basalt` barrel on its side | `tower` |
| Guardian lion statue | `stone_brick_stairs` on a `chiseled_sandstone` pedestal | `barracks`, `monastery`, `cathedral`, `harbor` +26 more |
| Clay pot, vase | `decorated_pot` | `courtyard_walls`, `harbor` |
| Prang (Khmer lotus-bud tower) | rings of `stone_bricks` and `chiseled_stone_bricks`, `gold_block` tip | `temple`, `harbor`, `hall_of_heroes`, `feitoria` +8 more |
| Checkered stone base | `polished_deepslate` in a checker pattern in the main stone | `caravanserai`, `stone_head` |
| Gilded dome | `gold_block` | `buddha_statue`, `dome_rock`, `ring`, `caravanserai` +15 more |
| Raised portal (pishtaq) of an arched gate | wall over the roof line, `chiseled_sandstone` frame, upside-down stairs as the arch | `pillar`, `statues`, `shrine`, `caravanserai` +9 more |
| Siege engine under construction | `spruce_slab`, `spruce_fence` and `spruce_log` | `dock`, `tower`, `market`, `barricade` +10 more |
| Stair to a roof terrace | `*_stairs` of the roof material | `storage`, `shelter`, `furnish_worship`, `town_hall` +37 more |
| Sail | `*_wool` (player color) | `pavilion`, `yurt`, `command_tent`, `army_tent` +19 more |
| Throne | stairs of the wood of the set, a carpet runner in the player color | no design |
| Ladder between floors | `ladder` | `keep_inside`, `outpost`, `tower`, `barracks` +1 more |
| Storage | `chest`, `barrel` | `decorate`, `town_hall`, `cart`, `keep_inside` +27 more |
| Armory | `grindstone`, `smithing_table` | `keep_inside`, `blacksmith`, `mill_room`, `decorate` +4 more |
| Light inside | `lantern` (hanging under a floor, or on the floor) | `hang`, `furnish`, `keep_inside`, `mill_room` +11 more |
| Rose window | `*_stained_glass_pane` | `monastery`, `fortified_church`, `cathedral` |
| Kitchen garden | `carrots`, `potatoes`, `wheat` (age 7) on `farmland`, `spruce_fence` with a `spruce_fence_gate` | `folwark` |
| Windmill sails | `spruce_fence` arms with `white_wool` cloth, `stripped_spruce_log` hub | `mill`, `folwark`, `market`, `command_tent` +4 more |

Add a row when a design uses a new feature block, with the block names in backticks. Put it after a row of a related
feature or design, not at the end of the table: parallel PRs that all add at the end get a merge conflict. Each new
block state must pass `mcvalid`. Do not edit "Used today in": `tools/feature_table.py` writes it on main from the
designs (the functions that place the most blocks of the row; a function that uses less than half of the names of the
best one is not listed).

## 3. Some noise

- Keep the variation of `vary()` (plaster, roof and timber per building), `weather()` (moss, cracks, similar
  stones and tiles) and `decorate()` (barrels, hay, lanterns next to the walls).
- The main block stays the large majority of each surface, so the building stays recognizable.
  Noise is a detail, not a pattern.
- New noise comes from the seeded `rng` (see rule 4). Never use `random` or a time-based seed.

## 4. The existing rules

- **Footprint and head height:** an object keeps its blocks inside its footprint up to 3 blocks above the ground.
  `Edits` removes other blocks. Roofs and eaves may stick out above head height.
- **Barriers:** `barriers()` fills the free space of the footprint. Units must never stand in a block: the
  converter prints "units in a block (moved up): N" and N must be 0.
- **Front on the south side:** the main door is at z = w-1. The default render view (`tools/render.py`,
  south-east) shows the front.
- **Deterministic output:** the same scenario and seed give the same world. Code that draws random numbers per
  block ID goes in state-name order (see `docs/LEARNINGS.md`).
- **Valid states:** each block state passes `mcvalid` (`tests/test_buildings.py` checks all designs).
