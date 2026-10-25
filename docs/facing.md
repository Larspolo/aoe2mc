# Check the facing of units

The converter turns the AoE2 rotation `r` (radians) of a unit into the Minecraft yaw
`atan2(-cos r, sin r)` (`units.make_entity`). Thus `r = 0` faces +x (east in Minecraft) and `r = π/2`
faces +z (south in Minecraft). The owner must compare this with the game once.

## The test map

`python3 tools/scenarios.py facing facing.aoe2scenario` makes a 32 × 32 map:

- 8 knights (player 1, blue) in a circle around tile (16.5, 16.5), radius 6 tiles. Knight k has the rotation
  k × π/4 and stands in the direction of that rotation from the center. With a correct converter,
  **each knight faces away from the center**.
- 8 archers (player 2, red) in a row at tile y = 27.5, from west to east, with the rotations 0, π/4 … 7π/4.
- A flag at tile (16.5, 3.5): the north edge of the Minecraft world (-z).

## The check

1. Make the map and convert it: `python3 aoe2mc.py facing.aoe2scenario FacingWorld`.
2. Open `facing.aoe2scenario` in the AoE2 DE scenario editor. Look at the 8 knights in the circle.
3. Write down if all knights face away from the center. If not, write down the direction of one knight
   relative to the center (for example "toward the center", "clockwise along the circle").
4. Open `FacingWorld` in Minecraft Java 1.21.1. The spawn is at the center of the circle. Look at the knights.
5. Compare. Also compare the row of archers: the first archer (west end) has rotation 0.
6. Comment the result on the check ticket. If the directions are different, the agent changes the formula
   and the test `test_facing_map_knights_face_away_from_the_center`.

Note: the AoE2 view is turned 45° (a diamond). Compare the directions relative to the circle center,
not relative to the screen.
