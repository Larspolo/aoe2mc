# Standard random maps of AoE2 DE

The random maps of the lobby group "Standard" of AoE2 DE and their state in the converter (item 2 of epic #4037).

- Source: the page [Random map](https://ageofempires.fandom.com/wiki/Random_map) of the AoE2 wiki, section
  "Age of Empires II", "Standard" (revision 1087306 of 2026-10-08; the MediaWiki API, as `tools/refimage.py` reads it).
  The rows are the land, hybrid, water, Capture the Relic, Battle Royale and other maps of that section.
- Script: the file name in the script folder of the owner's install (on a Mac:
  `AgeOfEmpires2Data/resources/_common/drs/gamedata_x2`; on Windows: `resources/_common/random-map-scripts`).
  `?`: the survey has no `.rms` file of that name (the map can be in an `.rms2` file or have another name).
- Own generator: `yes` when `rmap.GENERATORS` has a text for the map (`--random-map KIND`).
- State: the result of `python3 tools/rms_survey.py DIR` (item 1 of #4037) on the owner's 180 scripts
  (2026-10-29, main `a9007ee`, #4041): the first error, or "generates" and the count of warnings.
  Only 1 of 180 scripts (`Blind_Random`, not in this list) generates. The causes of the errors: the sub-issues of #4037.

| Map | Script | Own generator | State |
|---|---|---|---|
| Acclivity | `Acclivity.rms` | no | error: RmsError: unknown constant 'rnd(4,6)' |
| Acropolis | ? | no | no script in the survey |
| African Clearing | `AfricanClearing.rms` | no | error: RmsError: unknown constant 'LAYER_A' |
| Aftermath | `Aftermath.rms` | no | error: RmsError: unknown constant 'rnd(20,40)' |
| Alpine Lakes | `Alpine_Lakes.rms` | no | error: RmsError: unknown constant 'LAYER_A' |
| Amazon Tunnel | `AmazonTunnel.rms` | no | error: RmsError: unknown constant 'LAYER_A' |
| Aquarena | `Aquarena.rms` | no | error: RmsError: unknown constant 'LAYER_C' |
| Arabia | `Arabia.rms` | yes | error: ValueError: invalid literal for int() with base 10: '(PLAYER_FOREST_BASE_COUNT' |
| Archipelago | `Archipelago.rms` | no | error: RmsError: unknown constant 'VODA' |
| Arena | `Arena.rms` | yes | error: ValueError: invalid literal for int() with base 10: '(WALL_RADIUS' |
| Atacama | `Atacama.rms` | no | error: RmsError: unknown constant 'DLC_ROCK' |
| Baltic | `Baltic.rms` | no | error: RmsError: unknown constant 'WATER_SHALLOW' |
| Black Forest | `Black_Forest.rms` | yes | error: RmsError: unknown constant 'SPAWN_PLACEHOLDER' |
| Bog Islands | `Bog_Islands.rms` | no | error: RmsError: unknown constant 'DLC_MANGROVESHALLOW' |
| Bogland | `Bogland.rms` | no | error: ValueError: invalid literal for int() with base 10: '1.053' |
| Border Dispute | `Border Dispute.rms` | no | error: ValueError: invalid literal for int() with base 10: '#include_drs' |
| BR Battle On Ice | `BR_BattleontheIce.rms` | no | error: RmsError: unknown constant 'DLC_DRYGRASS' |
| BR El Dorado | `BR_ElDorado.rms` | no | error: RmsError: unknown constant 'DLC_JUNGLEGRASS' |
| BR Fall of Axum | `BR_FallofAxum.rms` | no | error: RmsError: unknown constant 'DLC_SAVANNAH' |
| BR Fall of Rome | `BR_FallofRome.rms` | no | error: RmsError: unknown constant 'DLC_DESERTGRAVEL' |
| BR Majapahit Empire | `BR_TheMajapahitEmpire.rms` | no | error: RmsError: unknown constant 'DLC_BEACH2' |
| Budapest | ? | no | no script in the survey |
| Cenotes | ? | no | no script in the survey |
| Chaos Pit | `Chaos Pit.rms` | no | error: RmsError: unknown constant 'BORDER_CONSTRAINT' |
| City of Lakes | ? | no | no script in the survey |
| Cliffbound | `Cliffbound.rms` | no | error: RmsError: unknown constant 'rnd(2,3)' |
| Coastal | `Coastal.rms` | no | error: RmsError: unknown constant 'WATER_SHALLOW' |
| Coastal Forest | `CoastalForest.rms` | no | error: RmsError: unknown constant 'WATER_SHALLOW' |
| Continental | `Continental.rms` | no | error: RmsError: an if or start_random has no end |
| Crater | `Crater.rms` | no | error: RmsError: unknown constant 'LAYER_A' |
| Crater Lake | `Crater_Lake.rms` | no | error: RmsError: unknown constant 'LAYER_A' |
| Crossroads | `Crossroads.rms` | no | error: RmsError: unknown constant 'DLC_DRYGRASS' |
| Crownwood | `Crownwood.rms` | no | error: RmsError: unknown constant '(32' |
| CtR Monsoon | ? | no | no script in the survey |
| CtR Pyramid Descent | ? | no | no script in the survey |
| CtR Random | ? | no | no script in the survey |
| CtR Spiral | ? | no | no script in the survey |
| Dorothea Quarry | `Dorothea Quarry.rms` | no | error: RmsError: unknown constant 'SHALLOWS' |
| Dunesprings | `Dunesprings.rms` | no | error: RmsError: unknown constant 'rnd(2,3)' |
| Enclosed | `Enclosed.rms` | no | error: RmsError: unknown constant 'rnd(4,6)' |
| Eruption | `Eruption.rms` | no | error: RmsError: unknown constant 'rnd(4,6)' |
| Fortified Clearing | `fortified_clearing.rms` | no | error: RmsError: unknown constant 'CIRCLE_BASE' |
| Fortress | `Fortress.rms` | no | error: RmsError: unknown constant 'LAYER_A' |
| Four Lakes | `FourLakes.rms` | no | error: RmsError: unknown constant 'VODA' |
| Frigid Lake | `FrigidLake.rms` | no | error: ValueError: max() iterable argument is empty |
| Ghost Lake | `Ghost_Lake.rms` | no | error: RmsError: unknown constant 'DLC_DRYGRASS' |
| Glacis | `Glacis.rms` | no | error: RmsError: unknown constant 'PLACEHOLDER_TERRAIN_B' |
| Glade | `Glade.rms` | no | error: RmsError: unknown constant '(EDGE_ELEVATION_CLUMPS' |
| Gold Rush | `Gold_Rush.rms` | yes | error: RmsError: endif without its start |
| Golden Pit | ? | no | no script in the survey |
| Golden Stream | `Golden_Stream.rms` | no | error: ValueError: max() iterable argument is empty |
| Golden Swamp | `GoldenSwamp.rms` | no | error: RmsError: unknown constant 'LAYER_A' |
| Graupel | `Graupel.rms` | no | error: RmsError: unknown constant 'WATER_SHALLOW' |
| Greenland | `Greenland.rms` | no | error: ValueError: invalid literal for int() with base 10: '0.72' |
| Haboob | `Haboob.rms` | no | error: RmsError: unknown constant 'rnd(2,4)' |
| Hamburger | ? | no | no script in the survey |
| Hengehold | `Hengehold.rms` | no | error: RmsError: unknown constant 'BASE_TERRAIN' |
| Hideout | ? | no | no script in the survey |
| Highland | `Highland.rms` | yes | error: RmsError: unknown constant 'VODA' |
| Hill Fort | ? | no | no script in the survey |
| Hollow Woodlands | `Hollow_Woodlands.rms` | no | error: RmsError: unknown constant 'rnd(2,3)' |
| Islands | `Islands.rms` | yes | error: RmsError: unknown constant 'LAYER_F' |
| Isthmus | `Isthmus.rms` | no | error: RmsError: unknown constant '(48' |
| Karsts | `Karsts.rms` | no | error: RmsError: endif without its start |
| Kawasan | `Kawasan.rms` | no | error: RmsError: unknown constant '(2048' |
| Kilimanjaro | `Kilimanjaro.rms` | no | error: ValueError: invalid literal for int() with base 10: '0.72' |
| Land Madness | `LandMadness.rms` | no | error: RmsError: unknown constant 'rnd(4,6)' |
| Land Nomad | `LandNomad.rms` | no | error: RmsError: unknown constant 'PLACEHOLDER_TERRAIN_A' |
| Lombardia | ? | no | no script in the survey |
| Lowland | `Lowland.rms` | no | error: RmsError: unknown constant 'rnd(4,6)' |
| Mangrove Jungle | `Mangrove_Jungle.rms` | no | error: RmsError: unknown constant 'DLC_NEWSHALLOW' |
| Marketplace | `Marketplace.rms` | no | error: ValueError: max() iterable argument is empty |
| Meadow | `Meadow.rms` | no | error: RmsError: unknown constant 'rnd(4,6)' |
| Mediterranean | `Mediterranean.rms` | yes | error: RmsError: unknown constant 'LAYER_A' |
| MegaRandom | ? | no | no script in the survey |
| Michi | `Michi.rms` | no | error: RmsError: unknown constant 'LAYER_C' |
| Migration | `Migration.rms` | no | error: ValueError: invalid literal for int() with base 10: '1.1' |
| Mongolia | `Mongolia.rms` | no | error: ValueError: invalid literal for int() with base 10: '0.72' |
| Morass | `Morass.rms` | no | error: RmsError: unknown constant 'rnd(2,3)' |
| Mountain Dunes | `Mountain_Dunes.rms` | no | error: RmsError: unknown constant 'rnd(1,2)' |
| Mountain Pass | `Mountain Pass.rms` | no | error: RmsError: unknown constant '(32' |
| Mountain Range | `MountainRange.rms` | no | error: RmsError: unknown constant 'rnd(45,55)' |
| Mountain Ridge | `Mountain_Ridge.rms` | no | error: RmsError: unknown constant 'LAYER_A' |
| Nile Delta | `Nile Delta.rms` | no | error: RmsError: unknown constant 'rnd(3,7)' |
| Nomad | `nomad.rms` | yes | error: ValueError: invalid literal for int() with base 10: '1.05' |
| Northern Isles | `NorthernIsles.rms` | no | error: ValueError: max() iterable argument is empty |
| Oasis | `Oasis.rms` | no | error: ValueError: invalid literal for int() with base 10: '(1' |
| Pacific Islands | `Pacific_Islands.rms` | no | error: RmsError: unknown constant 'DLC_WATER5' |
| Ravines | `Ravines.rms` | no | error: RmsError: unknown constant 'DLC_DESERTGRAVEL' |
| Ring Fortress | `RingFortress.rms` | no | error: RmsError: unknown constant 'SNOW_LIGHT' |
| River Divide | `River_Divide.rms` | no | error: RmsError: unknown constant 'rnd(2,3)' |
| Rivers | `Rivers.rms` | no | error: RmsError: unknown constant 'VODA' |
| Runestones | `Runestones.rms` | no | error: ValueError: invalid literal for int() with base 10: '0.72' |
| Sacred Springs | `SacredSprings.rms` | no | error: RmsError: unknown constant 'rnd(4,6)' |
| Salt Marsh | `Salt_Marsh.rms` | no | error: RmsError: unknown constant 'VODA' |
| Sandbank | `Sandbank.rms` | no | error: RmsError: unknown constant 'DLC_WATER5' |
| Sandrift | `Sandrift.rms` | no | error: RmsError: unknown constant 'rnd(2,3)' |
| Scandinavia | `Scandanavia.rms` | no | error: ValueError: invalid literal for int() with base 10: '(100' |
| Seize The Mountain | `SeizeTheMountain.rms` | no | error: RmsError: unknown constant 'LAYER_E' |
| Serengeti | `Serengeti.rms` | no | error: RmsError: unknown constant 'DLC_DIRT4' |
| Shoals | `Shoals.rms` | no | error: RmsError: unknown constant 'rnd(2,3)' |
| Shrubland | `Shrubland.rms` | no | error: RmsError: unknown constant 'rnd(2,3)' |
| Socotra | `Socotra.rms` | no | error: RmsError: 'override_map_size' before the first <SECTION> |
| Steppe | ? | no | no script in the survey |
| Team Islands | `Team_Islands.rms` | no | error: ValueError: invalid literal for int() with base 10: '1.1' |
| Team Moats | `TeamMoats.rms` | no | error: RmsError: unknown constant 'VODA' |
| The Passage | `The_Passage.rms` | no | error: RmsError: unknown constant 'rnd(2,3)' |
| Valley | ? | no | no script in the survey |
| Volcanic Island | `VolcanicIsland.rms` | no | error: RmsError: unknown constant 'LAYER_C' |
| Wade | `Wade.rms` | no | error: ValueError: max() iterable argument is empty |
| Water Nomad | `Water_Nomad.rms` | no | error: RmsError: unknown constant 'DLC_MANGROVESHALLOW' |
| Wolf Hill | `Wolf_Hill.rms` | no | error: RmsError: unknown constant 'DLC_DRYGRASS' |
| Yucatán | `Yucatan.rms` | no | error: RmsError: unknown constant 'WATER_SHALLOW' |

The other groups of the lobby have no rows: the "Real World" maps (28 maps, for example Britain, Iberia, Texas) and
the "Special" maps (for example Border Stones) are on the same page.

## Research: the labels of the game modes (#4824)

The AoE2 DE lobby defines one label for the game mode of a random map. `aoe2mc.py IN.rms OUT --game-mode MODE` defines
it too (`rmap.MODE_LABELS`), so that the `if LABEL` blocks of the script work. The source: the AoE2 DE random map
scripting guide and the labels that the real scripts test (`tools/rms_survey.py`, #4822). The objects of a mode (the
king, the monument) wait for #3846.

| Mode (`game/run.py`) | Label |
|---|---|
| battle-royale | `BATTLE_ROYALE` |
| capture-the-relic | `CAPTURE_THE_RELIC` |
| death-match | `DEATH_MATCH` |
| defend-the-wonder | `DEFEND_THE_WONDER` |
| empire-wars | `EMPIRE_WARS` |
| king-of-the-hill (`--victory`) | `KING_OT_HILL` |
| regicide | `REGICIDE` |
| standard | none |
| sudden-death | `SUDDEN_DEATH` |
| wonder-race | `WONDER_RACE` |

## Research: the other lobby labels (#5010)

The labels of the owner's survey (#4855) that the scripts test and no script defines, except the size, mode, player
and team labels (#4823, #4824, the player and team ticket). Source: the label counts of the survey (maps) and the use
of each label in the scripts. The cloud blocked the hosts of the DE scripting guide (`docs.google.com`,
`docs.racket-lang.org`, `plt.cs.northwestern.edu`, `twharris.dev`, 2026-10-31). The `/human` session of #5052 read the
guide ("Definitive Random Map Scripting Guide", Zetnus, section "Conditionals" → "Lobby Settings", 2026-10-31): "guide"
in the Source column names a label of that list, "not in the guide" a label that the list does not have. The list has
`0_TEAM_GAME` to `4_TEAM_GAME` and `TEAM_POSITIONS` (DE), but no `TEAM_GAME` and no `TEAMS_CONNECTED`.

| Label (maps) | Lobby setting | Option | Changes the land | Source |
|---|---|---|---|---|
| `ANTIQUITY_MODE` (80) | Antiquity Mode (Return of Rome rules) | `run.py --antiquity`; `aoe2mc.py --antiquity` (#5017) | yes (start objects) | survey, `run.py`, guide |
| `DARK_AGE_START` (83) | Starting age: Dark Age | `run.py --age`; `aoe2mc.py --age` (#5016) | yes (start objects) | survey, `run.py`, guide |
| `ENABLE_TREATY` (16) | Treaty length above 0 | `run.py --treaty` | no (game rule) | survey, `run.py`; not in the guide |
| `FIXED_POSITIONS` (3) | The lobby box "Team Together" is on (on in the DE lobby) | defined by default; `aoe2mc.py --no-team-together` (#5050) | yes (player places) | guide ("Additional lobby settings"); decision #5052 |
| `INFINITE_RESOURCES` (171) | Starting resources: Infinite | `run.py --resources`; `aoe2mc.py --resources` (#5016) | yes (mine and food amounts) | survey, `run.py`, guide |
| `LOW_RESOURCES` (10) | Starting resources: Low | `run.py --resources`; `aoe2mc.py --resources` (#5016) | yes (mine and food amounts) | survey, `run.py`, guide |
| `NOMAD_MAP` (77) | Nomad start (no town center) | `aoe2mc.py --nomad` (#5017) | yes (start objects) | survey; not in the guide (the guide has the map type `NOMAD`) |
| `TEAM_GAME`, `TEAMS_CONNECTED` (62, 23) | none: switches of the script authors, never defined: their `if` blocks stay off (#5050) | none | no (the lobby never defines them) | not in the guide; decision #5052 |
| `AZUREMASKING`, `EXTREME_ELEVATION`, `LEGACY_CODE`, `LEGACY_RELICS`, `NOMAD_CASTLE`, `NOMAD_HERDABLE`, `NOMAD_SCATTERED`, `NOMAD_TREATY`, `NOMAD_UNIT`, `REGICIDE_*` variants, `SEASONS_ALLOWMUDDYSHALLOWS`, `EMPIRE_WARS_*` variants, `*_ALLOW_FEEDING`, `DEBUG_MODE`, `TERRAIN_DEBUGGING`, `GNR_*`, `*_CAA_*` | none: switches of the script authors | none | no (the lobby never defines them) | survey |
