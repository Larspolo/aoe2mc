# New blocks in Minecraft 26.3

The blocks that Minecraft 26.3 has and 1.21.1 did not have: 227 blocks (#429). Source: the block lists of
`tools/mcdata/26.3.json` and of the old `tools/mcdata/1.21.1.json` (removed in #428, `git show 342e080^:tools/mcdata/1.21.1.json`).
The block properties are in parentheses (`waterlogged` is left out).
One block of 1.21.1 has a new name: `chain` is `iron_chain`.
The rows of the feature table in `docs/DESIGN.md` (section 2) say which AoE2 things these blocks fit.

## Wood sets: pale oak and poplar (44)

- `orange_poplar_leaves` (distance: 1/2/3/4/5/6/7, persistent: true/false)
- `pale_oak_button` (face: floor/wall/ceiling, facing: north/south/west/east, powered: true/false)
- `pale_oak_door` (facing: north/south/west/east, half: upper/lower, hinge: left/right, open: true/false, powered: true/false)
- `pale_oak_fence` (east: true/false, north: true/false, south: true/false, west: true/false)
- `pale_oak_fence_gate` (facing: north/south/west/east, in_wall: true/false, open: true/false, powered: true/false)
- `pale_oak_hanging_sign` (attached: true/false, rotation: 0/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15)
- `pale_oak_leaves` (distance: 1/2/3/4/5/6/7, persistent: true/false)
- `pale_oak_log` (axis: x/y/z)
- `pale_oak_planks`
- `pale_oak_pressure_plate` (powered: true/false)
- `pale_oak_sapling` (stage: 0/1)
- `pale_oak_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `pale_oak_sign` (rotation: 0/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15)
- `pale_oak_slab` (type: top/bottom/double)
- `pale_oak_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `pale_oak_trapdoor` (facing: north/south/west/east, half: top/bottom, open: true/false, powered: true/false)
- `pale_oak_wall_hanging_sign` (facing: north/south/west/east)
- `pale_oak_wall_sign` (facing: north/south/west/east)
- `pale_oak_wood` (axis: x/y/z)
- `poplar_button` (face: floor/wall/ceiling, facing: north/south/west/east, powered: true/false)
- `poplar_door` (facing: north/south/west/east, half: upper/lower, hinge: left/right, open: true/false, powered: true/false)
- `poplar_fence` (east: true/false, north: true/false, south: true/false, west: true/false)
- `poplar_fence_gate` (facing: north/south/west/east, in_wall: true/false, open: true/false, powered: true/false)
- `poplar_hanging_sign` (attached: true/false, rotation: 0/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15)
- `poplar_log` (axis: x/y/z)
- `poplar_planks`
- `poplar_pressure_plate` (powered: true/false)
- `poplar_sapling` (stage: 0/1)
- `poplar_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `poplar_sign` (rotation: 0/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15)
- `poplar_slab` (type: top/bottom/double)
- `poplar_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `poplar_trapdoor` (facing: north/south/west/east, half: top/bottom, open: true/false, powered: true/false)
- `poplar_wall_hanging_sign` (facing: north/south/west/east)
- `poplar_wall_sign` (facing: north/south/west/east)
- `poplar_wood` (axis: x/y/z)
- `potted_pale_oak_sapling`
- `potted_poplar_sapling`
- `red_poplar_leaves` (distance: 1/2/3/4/5/6/7, persistent: true/false)
- `stripped_pale_oak_log` (axis: x/y/z)
- `stripped_pale_oak_wood` (axis: x/y/z)
- `stripped_poplar_log` (axis: x/y/z)
- `stripped_poplar_wood` (axis: x/y/z)
- `yellow_poplar_leaves` (distance: 1/2/3/4/5/6/7, persistent: true/false)

## Shelves (11)

- `acacia_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `bamboo_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `birch_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `cherry_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `crimson_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `dark_oak_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `jungle_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `mangrove_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `oak_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `spruce_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)
- `warped_shelf` (facing: north/south/west/east, powered: true/false, side_chain: unconnected/right/center/left)

## Copper fittings (each in 4 ages, also waxed) (49)

- `copper_bars` (east: true/false, north: true/false, south: true/false, west: true/false)
- `copper_chain` (axis: x/y/z)
- `copper_chest` (facing: north/south/west/east, type: single/left/right)
- `copper_golem_statue` (copper_golem_pose: standing/sitting/running/star, facing: north/south/west/east)
- `copper_lantern` (hanging: true/false)
- `copper_torch`
- `copper_wall_torch` (facing: north/south/west/east)
- `exposed_copper_bars` (east: true/false, north: true/false, south: true/false, west: true/false)
- `exposed_copper_chain` (axis: x/y/z)
- `exposed_copper_chest` (facing: north/south/west/east, type: single/left/right)
- `exposed_copper_golem_statue` (copper_golem_pose: standing/sitting/running/star, facing: north/south/west/east)
- `exposed_copper_lantern` (hanging: true/false)
- `exposed_lightning_rod` (facing: north/east/south/west/up/down, powered: true/false)
- `oxidized_copper_bars` (east: true/false, north: true/false, south: true/false, west: true/false)
- `oxidized_copper_chain` (axis: x/y/z)
- `oxidized_copper_chest` (facing: north/south/west/east, type: single/left/right)
- `oxidized_copper_golem_statue` (copper_golem_pose: standing/sitting/running/star, facing: north/south/west/east)
- `oxidized_copper_lantern` (hanging: true/false)
- `oxidized_lightning_rod` (facing: north/east/south/west/up/down, powered: true/false)
- `waxed_copper_bars` (east: true/false, north: true/false, south: true/false, west: true/false)
- `waxed_copper_chain` (axis: x/y/z)
- `waxed_copper_chest` (facing: north/south/west/east, type: single/left/right)
- `waxed_copper_golem_statue` (copper_golem_pose: standing/sitting/running/star, facing: north/south/west/east)
- `waxed_copper_lantern` (hanging: true/false)
- `waxed_exposed_copper_bars` (east: true/false, north: true/false, south: true/false, west: true/false)
- `waxed_exposed_copper_chain` (axis: x/y/z)
- `waxed_exposed_copper_chest` (facing: north/south/west/east, type: single/left/right)
- `waxed_exposed_copper_golem_statue` (copper_golem_pose: standing/sitting/running/star, facing: north/south/west/east)
- `waxed_exposed_copper_lantern` (hanging: true/false)
- `waxed_exposed_lightning_rod` (facing: north/east/south/west/up/down, powered: true/false)
- `waxed_lightning_rod` (facing: north/east/south/west/up/down, powered: true/false)
- `waxed_oxidized_copper_bars` (east: true/false, north: true/false, south: true/false, west: true/false)
- `waxed_oxidized_copper_chain` (axis: x/y/z)
- `waxed_oxidized_copper_chest` (facing: north/south/west/east, type: single/left/right)
- `waxed_oxidized_copper_golem_statue` (copper_golem_pose: standing/sitting/running/star, facing: north/south/west/east)
- `waxed_oxidized_copper_lantern` (hanging: true/false)
- `waxed_oxidized_lightning_rod` (facing: north/east/south/west/up/down, powered: true/false)
- `waxed_weathered_copper_bars` (east: true/false, north: true/false, south: true/false, west: true/false)
- `waxed_weathered_copper_chain` (axis: x/y/z)
- `waxed_weathered_copper_chest` (facing: north/south/west/east, type: single/left/right)
- `waxed_weathered_copper_golem_statue` (copper_golem_pose: standing/sitting/running/star, facing: north/south/west/east)
- `waxed_weathered_copper_lantern` (hanging: true/false)
- `waxed_weathered_lightning_rod` (facing: north/east/south/west/up/down, powered: true/false)
- `weathered_copper_bars` (east: true/false, north: true/false, south: true/false, west: true/false)
- `weathered_copper_chain` (axis: x/y/z)
- `weathered_copper_chest` (facing: north/south/west/east, type: single/left/right)
- `weathered_copper_golem_statue` (copper_golem_pose: standing/sitting/running/star, facing: north/south/west/east)
- `weathered_copper_lantern` (hanging: true/false)
- `weathered_lightning_rod` (facing: north/east/south/west/up/down, powered: true/false)

## Stone: cinnabar and sulfur (28)

- `chiseled_cinnabar`
- `chiseled_sulfur`
- `cinnabar`
- `cinnabar_brick_slab` (type: top/bottom/double)
- `cinnabar_brick_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `cinnabar_brick_wall` (east: none/low/tall, north: none/low/tall, south: none/low/tall, up: true/false, west: none/low/tall)
- `cinnabar_bricks`
- `cinnabar_slab` (type: top/bottom/double)
- `cinnabar_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `cinnabar_wall` (east: none/low/tall, north: none/low/tall, south: none/low/tall, up: true/false, west: none/low/tall)
- `polished_cinnabar`
- `polished_cinnabar_slab` (type: top/bottom/double)
- `polished_cinnabar_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `polished_cinnabar_wall` (east: none/low/tall, north: none/low/tall, south: none/low/tall, up: true/false, west: none/low/tall)
- `polished_sulfur`
- `polished_sulfur_slab` (type: top/bottom/double)
- `polished_sulfur_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `polished_sulfur_wall` (east: none/low/tall, north: none/low/tall, south: none/low/tall, up: true/false, west: none/low/tall)
- `potent_sulfur` (potent_sulfur_state: dry/wet/dormant/erupting/continuous)
- `sulfur`
- `sulfur_brick_slab` (type: top/bottom/double)
- `sulfur_brick_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `sulfur_brick_wall` (east: none/low/tall, north: none/low/tall, south: none/low/tall, up: true/false, west: none/low/tall)
- `sulfur_bricks`
- `sulfur_slab` (type: top/bottom/double)
- `sulfur_spike` (thickness: tip_merge/tip/frustum/middle/base, vertical_direction: up/down)
- `sulfur_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `sulfur_wall` (east: none/low/tall, north: none/low/tall, south: none/low/tall, up: true/false, west: none/low/tall)

## Resin (7)

- `chiseled_resin_bricks`
- `resin_block`
- `resin_brick_slab` (type: top/bottom/double)
- `resin_brick_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `resin_brick_wall` (east: none/low/tall, north: none/low/tall, south: none/low/tall, up: true/false, west: none/low/tall)
- `resin_bricks`
- `resin_clump` (down: true/false, east: true/false, north: true/false, south: true/false, up: true/false, west: true/false)

## Wool and concrete slabs and stairs (16 colors) (64)

- `black_concrete_slab` (type: top/bottom/double)
- `black_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `black_wool_slab` (type: top/bottom/double)
- `black_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `blue_concrete_slab` (type: top/bottom/double)
- `blue_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `blue_wool_slab` (type: top/bottom/double)
- `blue_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `brown_concrete_slab` (type: top/bottom/double)
- `brown_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `brown_wool_slab` (type: top/bottom/double)
- `brown_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `cyan_concrete_slab` (type: top/bottom/double)
- `cyan_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `cyan_wool_slab` (type: top/bottom/double)
- `cyan_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `gray_concrete_slab` (type: top/bottom/double)
- `gray_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `gray_wool_slab` (type: top/bottom/double)
- `gray_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `green_concrete_slab` (type: top/bottom/double)
- `green_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `green_wool_slab` (type: top/bottom/double)
- `green_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `light_blue_concrete_slab` (type: top/bottom/double)
- `light_blue_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `light_blue_wool_slab` (type: top/bottom/double)
- `light_blue_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `light_gray_concrete_slab` (type: top/bottom/double)
- `light_gray_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `light_gray_wool_slab` (type: top/bottom/double)
- `light_gray_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `lime_concrete_slab` (type: top/bottom/double)
- `lime_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `lime_wool_slab` (type: top/bottom/double)
- `lime_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `magenta_concrete_slab` (type: top/bottom/double)
- `magenta_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `magenta_wool_slab` (type: top/bottom/double)
- `magenta_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `orange_concrete_slab` (type: top/bottom/double)
- `orange_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `orange_wool_slab` (type: top/bottom/double)
- `orange_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `pink_concrete_slab` (type: top/bottom/double)
- `pink_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `pink_wool_slab` (type: top/bottom/double)
- `pink_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `purple_concrete_slab` (type: top/bottom/double)
- `purple_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `purple_wool_slab` (type: top/bottom/double)
- `purple_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `red_concrete_slab` (type: top/bottom/double)
- `red_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `red_wool_slab` (type: top/bottom/double)
- `red_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `white_concrete_slab` (type: top/bottom/double)
- `white_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `white_wool_slab` (type: top/bottom/double)
- `white_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `yellow_concrete_slab` (type: top/bottom/double)
- `yellow_concrete_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)
- `yellow_wool_slab` (type: top/bottom/double)
- `yellow_wool_stairs` (facing: north/south/west/east, half: top/bottom, shape: straight/inner_left/inner_right/outer_left/outer_right)

## Plants and ground cover (18)

- `bush`
- `cactus_flower`
- `closed_eyeblossom`
- `firefly_bush`
- `golden_dandelion`
- `leaf_litter` (facing: north/south/west/east, segment_amount: 1/2/3/4)
- `open_eyeblossom`
- `pale_hanging_moss` (tip: true/false)
- `pale_moss_block`
- `pale_moss_carpet` (bottom: true/false, east: none/low/tall, north: none/low/tall, south: none/low/tall, west: none/low/tall)
- `potted_closed_eyeblossom`
- `potted_golden_dandelion`
- `potted_open_eyeblossom`
- `red_shrub`
- `shelf_mushroom` (age: 0/1, facing: north/south/west/east)
- `short_dry_grass`
- `tall_dry_grass`
- `wildflowers` (facing: north/south/west/east, flower_amount: 1/2/3/4)

## Other (6)

- `creaking_heart` (axis: x/y/z, creaking_heart_state: uprooted/dormant/awake, natural: true/false)
- `dried_ghast` (facing: north/south/west/east, hydration: 0/1/2/3)
- `iron_chain` (axis: x/y/z)
- `straw_bed` (facing: north/south/west/east, occupied: true/false, part: head/foot)
- `test_block` (mode: start/log/fail/accept)
- `test_instance_block`
