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
| Door, main entrance | `*_door` (front: south side), or an open arch for large gates | `pasture`, `tomb`, `yurt`, `house` +31 more |
| Window | `glass_pane`; `iron_bars` for fortified buildings | `barracks`, `ring`, `arena_inside`, `tower` +19 more |
| Archery target | `target` | `archery_range` |
| Bow and arrow work | `fletching_table` | `archery_range` |
| Forge, smithy | `blast_furnace`, `anvil`, `smithing_table`, `cauldron` (water) | `blacksmith` |
| Forge hearth, quench tub (inside) | `lava_cauldron` beside the chimney, `water_cauldron[level=3]` | `blacksmith`, `pasture`, `stable`, `caravanserai` |
| Fire, cooking | `campfire`, `smoker` | `decorate`, `hearth_room`, `burned_building`, `outpost` +7 more |
| Weapon rack, sharpening | `grindstone` | `mill_room`, `decorate`, `keep_inside`, `mining_camp` +8 more |
| Training dummy | `oak_fence`, `hay_block`, `carved_pumpkin` | `barracks`, `settlement`, `flagship`, `decorate` +12 more |
| Bell | `bell` | `town_center`, `fortified_church`, `monastery` |
| Bed (inside) | `*_bed` (player color), head to the north | `furnish`, `mill_room`, `hearth_room`, `lumber_camp` +3 more |
| Straw bed of a poor house, a camp or a barracks (inside) | `straw_bed` | `mill_room`, `lumber_camp`, `mining_camp`, `barracks` |
| Hearth in a hut or yurt | lit `campfire` in the middle (the smoke goes through the roof), `*_carpet` rugs around it | `hearth_room`, `furnish_worship`, `furnish`, `throne_hall` +24 more |
| Bedroll in a tent | `*_bed` (player color) on the floor along the canvas | `furnish`, `mill_room`, `hearth_room`, `lumber_camp` +3 more |
| Spears in a rack | `lightning_rod` | `nine_bands`, `storage`, `army_tent`, `feitoria` +21 more |
| Map table of a commander | `cartography_table` | `study`, `command_tent`, `harbor`, `market` +2 more |
| Cushion | `red_wool` next to a low `*_slab[type=top]` table | `pavilion`, `scaffold_walk`, `scaffolding`, `cart` +46 more |
| Table with a light (inside) | `*_slab[type=top]` with a `lantern` on it, a `*_stairs` stool | `town_hall`, `furnish`, `pagoda`, `hall_of_heroes` +41 more |
| Storage (inside) | `chest` at the back wall | `furnish`, `throne_hall`, `town_hall`, `decorate` +25 more |
| Shelf with goods or tools (inside) | `*_shelf` on the wall (holds items, like a stall) | `market`, `blacksmith` |
| Strongbox of a market or a treasury (inside) | `copper_chest` | no design |
| Rug | `*_carpet` | `hearth_room`, `furnish_worship`, `furnish`, `throne_hall` +15 more |
| Throne (inside) | `*_stairs` (backrest north) between `gold_block`s, `*_wall_banner`s (player color) over it | `throne_hall`, `pagoda`, `oracles_temple`, `feitoria` +37 more |
| Treasure (inside) | `chest` and `gold_block` in the back corners | `throne_hall`, `caravanserai`, `hall_of_heroes`, `harbor` +41 more |
| Statue in a hall (inside) | `chiseled_stone_bricks` base, `waxed_copper_block` and `waxed_cut_copper` (bronze) or `quartz_pillar` and `gold_block` (marble), lit `candle`s at its sides | `hall_of_heroes`, `dome_rock`, `furnish_worship`, `oracles_temple` +1 more |
| Tomb (inside) | `smooth_quartz` cenotaph with a `green_carpet` cloth on a `red_carpet`, lit `candle`s around it | `gol_gumbaz`, `temple_of_heaven`, `furnish_worship`, `dome_rock` +3 more |
| Arena (inside) | `sand` floor, seats that step down to it, a gate passage from the south, cells under the seats behind `iron_bars` with `hay_block`, `*_wall_banner`s and a `smooth_quartz_stairs` seat at the box of the emperor | `arena_inside`, `tower`, `barracks`, `granary` +14 more |
| Theatre stage (inside) | `dark_oak_slab` stage, `*_wall_banner`s behind it, `potted_fern`, `flower_pot`, `lantern`s | `arena_inside`, `market`, `town_hall`, `barracks` +4 more |
| Oracle's tripod (inside) | `cauldron` before the statue of the god, `decorated_pot`s (gifts) in the corners | `oracles_temple`, `decorate`, `barricade`, `hearth_room` +5 more |
| Idol on an altar (inside) | `gold_block` on `chiseled_sandstone`, lit `candle`s at its sides, `potted_poppy` offerings | `shrine`, `rekha_deul`, `dome_rock`, `furnish_worship` +9 more |
| Sanctum in a temple tower (inside) | `gold_block` idol on `chiseled_red_sandstone`, a path of `orange_carpet`, lit `candle`s, `potted_red_tulip` and `potted_orange_tulip` offerings | `rekha_deul` |
| Offering stone (outside) | `mossy_cobblestone` with a `skeleton_skull`, lit `candle`s, a `campfire` before it, skulls on carved posts | `pagan_shrine`, `svan_tower`, `oracles_temple` |
| Spiral stair in a tower (inside) | `*_stairs` around a 2 × 2 shaft, one step per block, a hanging `lantern` under every 6th step | `furnish_worship`, `town_hall`, `furnish`, `keep_inside` +57 more |
| Bench (inside) | `*_stairs` in a row | `storage`, `shelter`, `furnish_worship`, `town_hall` +43 more |
| Sacred rock in a shrine (inside) | `stone`, `andesite` and `tuff` in a low mound, lit `candle`s around it, a ring of `quartz_pillar` columns | `dome_rock`, `stonehenge` |
| Hay loft (inside) | `spruce_slab[type=top]` with `hay_block` on it | `settlement`, `cart`, `flagship`, `stable` +31 more |
| Light on a wall (inside) | `wall_torch` | `town_hall`, `archery_range`, `stable` |
| Loom, cloth | `loom`, wool | `decorate`, `command_tent`, `dock`, `harbor` |
| Market goods | `barrel`, `chest`, `composter`, `hay_block`, `melon`, `pumpkin` | `market`, `decorate`, `settlement`, `harbor` +14 more |
| Bales of trade goods (inside) | `*_wool` and `hay_block`, stacked in corners and along walls | `pasture`, `cart`, `flagship`, `tower` +37 more |
| Counting room (inside) | `cartography_table` with a `lantern`, `lectern[has_book=true]` | `market`, `feitoria`, `keep_inside`, `throne_hall` +6 more |
| Market stall | lean-to of roof stairs on `*_fence` posts; wool awning in stripes for flat-roof sets | `fish_trap`, `nine_bands`, `outpost`, `flagship` +38 more |
| Cloth awning or tent roof that slopes | `*_wool_stairs` and `*_wool_slab` (player color or `white_*`) | `command_tent`, `pasture`, `stupa`, `army_tent` +22 more |
| Upper floor (inside) | `*_planks` floor and a `ladder` | `helepolis`, `tower`, `wooden_fort`, `outpost` +39 more |
| Painted trim (deck edge, band) | `*_concrete` (player color) | `torii`, `stupa`, `pyramid`, `feitoria` +2 more |
| Painted plaster roof or ledge | `*_concrete_stairs` and `*_concrete_slab` | no design |
| Red-painted stone (Indian, Mesoamerican, East Asian temples) | `cinnabar`, `cinnabar_bricks`, `polished_cinnabar`, `chiseled_cinnabar` | `rekha_deul`, `pagoda` |
| Yellow ochre stone (African, Middle Eastern sets) | `sulfur_bricks`, `polished_sulfur`, `chiseled_sulfur` | `sankore` |
| Fired orange brick | `resin_bricks`, `chiseled_resin_bricks` | `split_gate` |
| Relief panel, carving | `chiseled_stone_bricks` | `harbor`, `temple`, `aqueduct`, `furnish_worship` +9 more |
| Balustrade of a stair | `polished_granite` | `great_pyramid`, `pyramid` |
| Stone bridge (#455) | `stone_bricks` piers with cutwaters every tile, `stone_brick_stairs[half=top]` vault, `stone_brick_wall` balustrade with `chiseled_stone_bricks` posts, `cracked_stone_bricks` on cracked and broken pieces | `bridge`, `temple`, `cathedral`, `fortified_church` +18 more |
| Crop field | `wheat` rows (ages 5–7) on `farmland`, furrows of bare `farmland`, `dirt_path` edge | `folwark` |
| Hay, fodder | `hay_block` | `settlement`, `hut`, `mill_room`, `granary` +20 more |
| Fallen leaves in a forest | `leaf_litter[segment_amount=1-4]` under the trees | no design |
| Meadow flowers, flower field | `wildflowers[flower_amount=1-4]`, `golden_dandelion` | no design |
| Dry steppe or desert grass | `short_dry_grass`, `tall_dry_grass` | no design |
| Desert cactus in bloom | `cactus` with a `cactus_flower` on top | no design |
| Shrub (`BUSH`, `PLANT_SHRUB`) | `bush`, `red_shrub`; `firefly_bush` near water (lights at night) | no design |
| Bracket fungus on an old tree | `shelf_mushroom` on the trunk | no design |
| Pale timber (birch-like boards) | `pale_oak_planks`, `pale_oak_log` | no design |
| Poplar (Mediterranean tree, autumn colors) | `poplar_log`, `yellow_poplar_leaves`, `orange_poplar_leaves`, `red_poplar_leaves` | no design |
| Log pile, cut timber | `*_log[axis=x]` stacked as a pyramid (`log_pile`) | `log_pile`, `wooden_bridge`, `crane`, `shelter` +37 more |
| Debris heap of a barricade | `cobblestone`, `andesite`, `spruce_log`, `stripped_spruce_log`, `spruce_planks`, `spruce_slab`; on top `mangrove_roots` (branches), `spruce_fence`, `oak_leaves` (ivy), `barrel`, `decorated_pot` | `barricade`, `market`, `dock`, `tower` |
| Wooden bridge: boards across the bridge, posts over the deck | `stripped_spruce_log[axis=*]` and `spruce_planks` in turn, `stripped_oak_log` posts every second block, no railing | `wooden_bridge`, `shipyard`, `dock`, `stable` +17 more |
| Hoist | a log post and arm, `iron_chain`, a hanging log | `harbor_chain`, `hang`, `crane`, `lumber_camp` +4 more |
| Workbench | `crafting_table` | `lumber_camp`, `shipyard`, `dock`, `siege_workshop` |
| Millstone | `grindstone` | `mill_room`, `decorate`, `keep_inside`, `mining_camp` +8 more |
| Drive shaft of a windmill | `stripped_spruce_log[axis=y]` above the millstone | `crane`, `mill_room`, `barricade`, `wooden_bridge` +18 more |
| Net loom, boat workbench | `loom`, `crafting_table`, `spruce_slab` | `dock`, `siege_workshop` |
| Dried fish, ship timber | `dried_kelp_block`, `stripped_spruce_log` (stack on the quay) | `crane`, `mill_room`, `barricade`, `wooden_bridge` +19 more |
| Light in a room or a yard | `lantern` on a barrel, or hanging under a beam | `hang`, `keep_inside`, `furnish`, `mill_room` +36 more |
| Ore, mined gold and stone | `gold_ore`, `raw_gold_block`, `cobblestone`, `stone`, `andesite` | `mining_camp`, `mole` |
| Mine cart track | `rail` | `mining_camp` |
| Water trough | `cauldron` (water) | `decorate`, `svan_tower`, `oracles_temple` |
| Fountain | `water` source in a 3 × 3 rim of `stone_bricks` (`smooth_quartz` for antiquity), posts on the corners | `theatre`, `tower`, `monastery`, `feitoria` +40 more |
| Bench | three `*_stairs` in a row | `storage`, `shelter`, `furnish_worship`, `town_hall` +43 more |
| Clay pots, amphorae, water pots | `decorated_pot`, `water_cauldron` | `barricade`, `hearth_room`, `pasture`, `tomb` +7 more |
| Banner, flag | `*_banner` (player color), `Canvas.flag` | `throne_hall`, `town_hall`, `keep_inside`, `arena_inside` +58 more |
| Player color band (walls, gate towers) | `*_wool` (player color), one row | `yurt`, `pavilion`, `command_tent`, `pasture` +23 more |
| Fence, pen | `*_fence` | `fish_trap`, `nine_bands`, `outpost`, `flagship` +38 more |
| Gate of a pen | `*_fence_gate` | `folwark` |
| Trodden ground of a pasture | patches of `coarse_dirt` and `rooted_dirt`, low `spruce_fence` stakes | `sapper_tunnel`, `pasture`, `lumber_camp`, `pagan_shrine` +1 more |
| Fish trap basket | `bamboo_fence` rods on half-round hoops of `dark_oak_wood` and `stripped_oak_wood` | `fish_trap` |
| Wheel | open `*_trapdoor` on the side | `cart`, `university`, `market`, `yurt` +11 more |
| Siege engine in the making | `stripped_spruce_log` frame, `oak_fence` posts, a `stripped_oak_log` ram beam with an `iron_block` head | `siege_workshop`, `shipyard`, `hall_with_yard`, `stable` +17 more |
| Tent canvas | `white_wool`, a valance of wool in the player color | `command_tent`, `pasture`, `army_tent`, `pavilion` +8 more |
| Tent poles of a pavilion | `stripped_spruce_log[axis=y]` at the corners, up to the roof edge | `crane`, `mill_room`, `barricade`, `wooden_bridge` +18 more |
| Lookout hut on stilts (outpost) | `*_log` stilts with `spruce_fence` braces, a `*_wool` band (player color) and `white_wool` cloth, a `white_wool` roof with a valance (player color) | `outpost`, `folwark`, `mill`, `market` +11 more |
| Yurt felt | `blue_wool` with a zig-zag of `white_wool` (or the inverse), a flat dome with a `spruce_trapdoor` crown ring | `yurt`, `pasture`, `market`, `pavilion` +8 more |
| Pavilion cloth | stripes of `*_wool` (player color) on `white_wool`, a `yellow_wool` valance, a white cone | `pavilion`, `command_tent`, `pasture`, `army_tent` +8 more |
| Thatch | `hay_block` | `settlement`, `hut`, `mill_room`, `granary` +20 more |
| Wicker wall of a hut | `mangrove_roots` between `spruce_log[axis=y]` posts | `hut`, `barricade`, `log_pile`, `shipyard` +22 more |
| Palisade stakes | `*_log[axis=y]` of two heights, `spruce_fence` tips | `crane`, `outpost`, `barricade`, `dock` +41 more |
| Gold statue, finial | `gold_block` | `buddha_statue`, `throne_hall`, `dome_rock`, `ring` +17 more |
| Painted wood (torii) | `red_concrete`, `black_concrete` pillar feet, a `spruce_planks` bark top with `spruce_stairs` upturned ends | `torii`, `wooden_fort`, `dock`, `storage` +7 more |
| Name plaque (torii) | `blue_stained_glass_pane` between the beams | `torii`, `cathedral` |
| Climbing plants | `vine`, `azalea_leaves` | `pillar`, `garden` |
| Charred timber | `coal_block`, `blackstone`, dark oak logs | `burned_building` |
| Scaffolding, building site | `scaffolding` posts, `spruce_slab` decks, `ladder` | `scaffold_walk`, `scaffolding`, `tower`, `market` |
| Standing stones with lintels | `stone`, `andesite`, `tuff` posts, a ring of `stone` on top | `stonehenge`, `dome_rock`, `mole`, `mining_camp` +7 more |
| Stone seats of a theatre | `stone_bricks` rising outward, `smooth_stone` and slabs on top | `theatre`, `fortified_church`, `port`, `donjon` +43 more |
| Spire tip, finial | `lightning_rod` | `nine_bands`, `storage`, `army_tent`, `feitoria` +21 more |
| Copper roof, copper dome | `weathered_cut_copper`, `weathered_copper` | `cathedral` |
| Slate spire | `deepslate_tiles` | `hall_of_heroes`, `cathedral` |
| Pinnacle | the `accent_wall` of the style (`*_wall`) | `ring`, `garden`, `courtyard_walls`, `storage` +23 more |
| Striped marble | rows of `polished_deepslate` in the main stone | `caravanserai`, `stone_head` |
| Mud-brick pinnacle | `mud_brick_wall` on a buttress | `garden`, `storage`, `sankore`, `djenne` +15 more |
| Glazed tile band, tile panel | `blue_terracotta`; `Style.dome` terracotta over arches | `minaret_of_jam`, `caravanserai`, `dome_rock`, `gol_gumbaz` +1 more |
| Chhatri (small domed kiosk) | `quartz_pillar` posts and a small dome | `throne_hall`, `oracles_temple`, `arch_of_constantine`, `theatre` +3 more |
| Chain, rope | `iron_chain` | `harbor_chain`, `hang`, `crane`, `lumber_camp` +4 more |
| Bartizan (corner turret) | stone, `smooth_quartz` cap, `lightning_rod` | `temple_of_heaven`, `taj`, `stupa`, `dome_rock` +26 more |
| Terracotta roof (Portuguese, Sicilian, Polish) | `brick` stairs | `oracles_temple`, `folwark`, `svan_tower`, `shelter` +13 more |
| Portcullis, grille | `iron_bars` | `arena_inside`, `tower`, `donjon`, `krepost` +4 more |
| Wooden hoarding | wood slab (top) or `spruce_planks` with a `*_fence` rail | `helepolis`, `crane`, `shipyard`, `outpost` +48 more |
| Coat of arms | `*_wall_banner` (player color) over the gate | `throne_hall`, `town_hall`, `keep_inside`, `arena_inside` +42 more |
| Lamp | `lantern` | `hang`, `keep_inside`, `furnish`, `mill_room` +36 more |
| Lamp inside a room | `lantern[hanging=true]` under a ceiling, or on an `iron_chain` | `hang`, `lumber_camp`, `shipyard`, `blacksmith` +39 more |
| Copper lamp, grille and chain (rich buildings; they turn green with age) | `copper_lantern`, `copper_bars`, `copper_chain`, `copper_torch`, and the `exposed_*`, `weathered_*`, `oxidized_*` forms | `cathedral` |
| Cloth awning | `*_wool` in the player color | `yurt`, `pavilion`, `command_tent`, `pasture` +23 more |
| Column | `quartz_pillar` | `throne_hall`, `oracles_temple`, `arch_of_constantine`, `theatre` +3 more |
| Sacred tree | `oak_log`, `oak_leaves[persistent=true]` | `pagan_shrine`, `log_pile`, `decorate`, `house` +4 more |
| Hides | `brown_wool` | `helepolis`, `market`, `feitoria` |
| Nomad hide tent | `brown_wool` dome and peak, an ornament band of `white_wool` and `orange_wool`, `red_carpet` rug | `caravanserai`, `market`, `feitoria` |
| Band in the player color | `*_wool` (player color) | `yurt`, `pavilion`, `command_tent`, `pasture` +23 more |
| Outside stairs to an upper floor | `*_stairs` of the wood of the set | `storage`, `shelter`, `furnish_worship`, `town_hall` +43 more |
| Books, study | `bookshelf`, `lectern` (with a book) | `library`, `sankore`, `university`, `town_hall` +5 more |
| Desks, light inside | `enchanting_table`, `cartography_table`, `candle` (lit, on shelves and desks), `lantern` on an `iron_chain` (`hang()`) | `study`, `hang`, `furnish_worship`, `lumber_camp` +16 more |
| Ledger and trade maps (inside) | `lectern` (with a book) and `cartography_table` on a counter of top slabs | `market`, `feitoria`, `study`, `library` +9 more |
| Scholar statue | `chiseled_stone_bricks` pedestal, `quartz_pillar`, `chiseled_quartz_block` | `university`, `oracles_temple`, `arch_of_constantine`, `theatre` |
| Posts of an open belfry | `stone_brick_wall` | `ring`, `bridge`, `temple`, `barracks` +3 more |
| Orange roof tiles (Krepost; Central European, Southeast Asian sets) | `red_sandstone` stairs and blocks | `storage`, `fortified_church`, `shelter`, `taj` +25 more |
| Stepped stone roof (Mesoamerican set) | `stone_brick` stairs (hip roof) | `bridge`, `shelter`, `storage`, `temple` +18 more |
| Thatch or shingle roof (East Asian set) | `spruce` stairs | `pagoda`, `tomb`, `furnish_worship`, `wooden_fort` +15 more |
| Cannon | `polished_basalt` barrel on its side | `tower` |
| Guardian lion statue | `stone_brick_stairs` on a `chiseled_sandstone` pedestal | `barracks`, `monastery`, `cathedral`, `harbor` +27 more |
| Clay pot, vase | `decorated_pot` | `barricade`, `hearth_room`, `tomb`, `courtyard_walls` +3 more |
| Prang (Khmer lotus-bud tower) | rings of `stone_bricks` and `chiseled_stone_bricks`, `gold_block` tip | `temple`, `harbor`, `hall_of_heroes`, `feitoria` +10 more |
| Checkered stone base | `polished_deepslate` in a checker pattern in the main stone | `caravanserai`, `stone_head` |
| Gilded dome | `gold_block` | `buddha_statue`, `throne_hall`, `dome_rock`, `ring` +17 more |
| Raised portal (pishtaq) of an arched gate | wall over the roof line, `chiseled_sandstone` frame, upside-down stairs as the arch | `pillar`, `statues`, `caravanserai`, `sanchi_stupa` +9 more |
| Siege engine under construction | `spruce_slab`, `spruce_fence` and `spruce_log` | `barricade`, `dock`, `tower`, `market` +11 more |
| Stair to a roof terrace | `*_stairs` of the roof material | `storage`, `shelter`, `furnish_worship`, `town_hall` +43 more |
| Sail | `*_wool` (player color) | `yurt`, `pavilion`, `command_tent`, `pasture` +23 more |
| Throne | stairs of the wood of the set, a carpet runner in the player color | no design |
| Ladder between floors | `ladder` | `keep_inside`, `scaffold_walk`, `outpost`, `scaffolding` +6 more |
| Storage | `chest`, `barrel` | `decorate`, `town_hall`, `cart`, `keep_inside` +36 more |
| Armory | `grindstone`, `smithing_table` | `keep_inside`, `blacksmith`, `siege_workshop`, `mill_room` +8 more |
| Light inside | `lantern` (hanging under a floor, or on the floor) | `hang`, `keep_inside`, `furnish`, `mill_room` +36 more |
| Rose window | `*_stained_glass_pane` | `torii`, `monastery`, `fortified_church`, `cathedral` |
| Kitchen garden | `carrots`, `potatoes`, `wheat` (age 7) on `farmland`, `spruce_fence` with a `spruce_fence_gate` | `folwark` |
| Windmill sails | `spruce_fence` arms with `white_wool` cloth, `stripped_spruce_log` hub | `mill`, `folwark`, `market`, `pasture` +8 more |

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

## 5. Units

### Siege units

A siege unit is a minecart on a carrier mob of the game program (#836). The mob in the minecart (the crew) gives each
siege unit its own look (owner decision on #1525: "Minecart but with D as well for the mob in the minecart. War wagon a
horse in the minecart", #1664). The crew has the hit points and the name line. It keeps `NoAI` and `Silent`: it does
not walk, jump, shoot, attack or make sounds by itself. `units.SIEGE_CREW` holds the table.

| AoE2 unit | Mob in the minecart | Scale | Note |
|---|---|---|---|
| Battering Ram, Capped Ram, Siege Ram | `iron_golem` | 0.5, 0.55, 0.6 | 1.0, 1.1, 1.2 × the battering ram |
| Mangonel, Onager, Siege Onager | `breeze` | 0.8 | |
| Scorpion, Heavy Scorpion | `piglin` with a crossbow | 1.0 | `IsImmuneToZombification` 1 |
| Trebuchet | `warden` | 0.6 unpacked, 0.36 packed | `game/trebuchet.py` sets the size when a pack or an unpack ends |
| Bombard Cannon, Houfnice | `ghast` | 0.3 | |
| Siege Tower | `sniffer` | 0.5 | the units inside ride the crew (`game/siege_tower.py`) |
| Organ Gun, Rocket Cart, Cobra Car, Hussite Wagon | unchanged | 1.0 | a cart with the present crew |

The War Wagon and the Elite War Wagon are no siege units in AoE2 (armor classes cavalry and archer): one `horse` pulls
a cart (owner, #2737; AoE2 has two horses). The horse is the unit: it walks with `aoe moveto`, has the hit points and
the name line, and shoots as a siege unit of the plugin (blast 0, `combat.range_command`). The cart is an
`item_display` of a `chest` that rides the horse, behind it and down on the ground (`units.cart`, `CART_AT`,
`CART_SCALE`). Its item has the `custom_model_data` `aoe2mc:war_wagon`: without a resource pack it is a vanilla chest;
with `--resource-pack` the pack draws the cart model (`aoe2mc.cart_model`: plank walls, an iron rim, a plank roof,
two wheels). A passenger keeps its own rotation, so the plugin turns the cart with its horse each tick (#2746).
