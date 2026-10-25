# Design guide

These rules apply to all design work: buildings, objects, units and animals.
The owner set them on 2026-10-25 (#40):

> I want all the buildings to look as close to in-game as possible while also keeping it making sense. So if there
> should be a door, use a door, for a target use the target block, etc. Also some noise should still exist so it
> doesn't look so plain.

The `design` skill (`.claude/skills/design/SKILL.md`) gives the steps of one design ticket.

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
| Door, main entrance | `*_door` (front: south side), or an open arch for large gates | `Canvas.door`, `town_center` |
| Window | `glass_pane`; `iron_bars` for fortified buildings | `Canvas.windows`, `house`, `monastery`; `castle`, `tower` |
| Archery target | `target` | `archery_range` |
| Bow and arrow work | `fletching_table` | `archery_range` |
| Forge, smithy | `blast_furnace`, `anvil`, `smithing_table`, `cauldron` (water) | `blacksmith` |
| Fire, cooking | `campfire`, `smoker` | `blacksmith`, `house`, `outpost`, `church`, `oracles_temple`, `pyramid` (braziers) |
| Weapon rack, sharpening | `grindstone` | `barracks`, `granary`, `blacksmith` |
| Training dummy | `oak_fence`, `hay_block`, `carved_pumpkin` | `barracks` |
| Bell | `bell` | `monastery`, `town_center` |
| Bed (inside) | `*_bed` (player color), head to the north | `house` (`furnish`) |
| Table with a light (inside) | `*_slab[type=top]` with a `lantern` on it, a `*_stairs` stool | `house` (`furnish`) |
| Storage (inside) | `chest` at the back wall | `house` (`furnish`) |
| Rug | `*_carpet` | `house` (`furnish`) |
| Loom, cloth | `loom`, wool | `church` |
| Market goods | `barrel`, `chest`, `composter`, `hay_block`, `melon`, `pumpkin` | `market`, `dock`, `harbor` |
| Market stall | lean-to of roof stairs on `*_fence` posts; wool awning in stripes for flat-roof sets | `market` |
| Painted trim (deck edge, band) | `*_concrete` (player color) | `dock`, `pyramid` |
| Relief panel, carving | `chiseled_stone_bricks` | `pyramid` |
| Balustrade of a stair | `polished_granite` | `pyramid` |
| Hoist | log beam with `chain` | `dock` |
| Crop field | `wheat` rows (ages 5–7) on `farmland`, furrows of bare `farmland`, `dirt_path` edge | farm (`place_building`) |
| Hay, fodder | `hay_block` | `stable`, `barracks`, `granary` |
| Log pile, cut timber | `*_log[axis=x]` stacked as a pyramid (`log_pile`) | `lumber_camp` |
| Hoist | a log post and arm, `chain`, a hanging log | `lumber_camp` |
| Workbench | `crafting_table` | `lumber_camp` |
| Millstone | `grindstone` | `mill`, `mining_camp` (tools) |
| Ore, mined gold and stone | `gold_ore`, `raw_gold_block`, `cobblestone`, `stone`, `andesite` | `mining_camp` |
| Mine cart track | `rail` | `mining_camp` |
| Water trough | `cauldron` (water) | `stable` |
| Banner, flag | `*_banner` (player color), `Canvas.flag` | most designs |
| Player color band (walls, gate towers) | `*_wool` (player color), one row | `wall_segment`, `gate` |
| Fence, pen | `*_fence` | `stable`, `market`, `outpost`, `wall_segment` |
| Gate of a pen | `*_fence_gate` | `pasture` |
| Wheel | open `*_trapdoor` on the side | `cart` |
| Tent canvas | `white_wool`, a valance of wool in the player color | `army_tent`, `command_tent` |
| Thatch | `hay_block` | `hut`, `settlement`, `tower` (African) |
| Palisade stakes | `*_log[axis=y]` of two heights, `spruce_fence` tips | `wooden_fort`, `wall_segment`, `gate` |
| Gold statue, finial | `gold_block` | `buddha_statue`, `stupa`, `monument`, `temple` |
| Painted wood (torii) | `red_concrete`, black top beam | `torii` |
| Climbing plants | `vine`, `azalea_leaves` | `pillar` |
| Charred timber | `coal_block`, `blackstone`, dark oak logs | `burned_building` |
| Spire tip, finial | `lightning_rod` | `Canvas.spire`, `monastery`, `mosque` |
| Copper roof, copper dome | `weathered_cut_copper`, `weathered_copper` | `cathedral` |
| Slate spire | `deepslate_tiles` | `cathedral` |
| Pinnacle | the `accent_wall` of the style (`*_wall`) | `cathedral` |
| Striped marble | rows of `polished_deepslate` in the main stone | `cathedral` (Mediterranean) |
| Mud-brick pinnacle | `mud_brick_wall` on a buttress | `djenne` (Wonder, African) |
| Glazed tile band, tile panel | `blue_terracotta`; `Style.dome` terracotta over arches | `taj`, `samarra` (Wonders) |
| Chhatri (small domed kiosk) | `quartz_pillar` posts and a small dome | `taj` (Wonder, South Asian) |
| Chain, rope | `chain` | `dock`, `siege_workshop`, `shipyard`, `harbor_chain` |
| Bartizan (corner turret) | stone, `smooth_quartz` cap, `lightning_rod` | `feitoria` |
| Terracotta roof (Portuguese, Sicilian, Polish) | `brick` stairs | `feitoria`, `donjon`, `folwark` |
| Portcullis, grille | `iron_bars` | `gate`, `castle`, `krepost` |
| Wooden hoarding | wood slab (top) or `spruce_planks` with a `*_fence` rail | `donjon`, `krepost` |
| Coat of arms | `*_wall_banner` (player color) over the gate | `donjon` |
| Lamp | `lantern` | `decorate()`, `blacksmith` (hanging), `pagoda` (under the eaves) |
| Siege engine under construction | spruce slabs, fences and logs | `siege_workshop` |
| Cloth awning | `*_wool` in the player color | `house` (flat roofs) |
| Stair to a roof terrace | stairs of the roof material | `house` (flat roofs) |
| Column | `quartz_pillar` | `arch_of_constantine`, `oracles_temple` |
| Sacred tree | `oak_log`, `oak_leaves[persistent=true]` | `pagan_shrine` |
| Sail | wool (player color) | `flagship` |
| Hides | `brown_wool` | `helepolis` |
| Band in the player color | `*_wool` (player color) | `town_center`, `castle`, `tower`, `temple`, `pagoda` |
| Outside stairs to an upper floor | `*_stairs` of the wood of the set | `town_center` |
| Books, study | `bookshelf`, `lectern` (with a book) | `university` |
| Scholar statue | `chiseled_stone_bricks` pedestal, `quartz_pillar`, `chiseled_quartz_block` | `university` |
| Rose window | stained glass panes | `monastery` |
| Posts of an open belfry | `stone_brick_wall` | `fortified_church` |
| Orange roof tiles (Krepost; Central European, Southeast Asian sets) | `red_sandstone` stairs and blocks | `krepost`, `fortified_church`, `Style.roof` |
| Stepped stone roof (Mesoamerican set) | `stone_brick` stairs (hip roof) | `Style.roof` |
| Thatch or shingle roof (East Asian set) | `spruce` stairs | `Style.roof` |
| Cannon | `polished_basalt` barrel on its side | `tower` (bombard) |
| Guardian lion statue | `stone_brick_stairs` on a `chiseled_sandstone` pedestal | `harbor` |
| Clay pot, vase | `decorated_pot` | `harbor` |
| Prang (Khmer lotus-bud tower) | rings of `stone_bricks` and `chiseled_stone_bricks`, `gold_block` tip | `temple`, `harbor` |
| Checkered stone base | `polished_deepslate` in a checker pattern in the main stone | `caravanserai` |
| Gilded dome | `gold_block` | `caravanserai` |
| Raised portal (pishtaq) of an arched gate | wall over the roof line, `chiseled_sandstone` frame, upside-down stairs as the arch | `caravanserai` |
| Kitchen garden | `carrots`, `potatoes`, `wheat` (age 7) on `farmland`, `spruce_fence` with a `spruce_fence_gate` | `folwark` |
| Windmill sails | `spruce_fence` arms with `white_wool` cloth, `stripped_spruce_log` hub | `mill`, `folwark` |

Add a line when a design uses a new feature block. Each new block state must pass `mcvalid`.

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
