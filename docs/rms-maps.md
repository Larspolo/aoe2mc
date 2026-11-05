# Standard random maps of AoE2 DE

The random maps of the lobby group "Standard" of AoE2 DE and their state in the converter (item 2 of epic #4037).

- Source: the page [Random map](https://ageofempires.fandom.com/wiki/Random_map) of the AoE2 wiki, section
  "Age of Empires II", "Standard" (revision 1087306 of 2026-10-08; the MediaWiki API, as `tools/refimage.py` reads it).
  The rows are the land, hybrid, water, Capture the Relic, Battle Royale and other maps of that section.
- Script: the file name in the script folder of the owner's install (on a Mac:
  `AgeOfEmpires2Data/resources/_common/drs/gamedata_x2`; on Windows: `resources/_common/random-map-scripts`).
  A name with no ending: a script that the first survey did not read (`.rms` or `.rms2`, #5363).
- Own generator: `yes` when `rmap.GENERATORS` has a text for the map (`--random-map KIND`).
- State: the result of `python3 tools/rms_survey.py DIR` (item 1 of #4037) on the owner's 196 scripts
  (2026-11-05, main `7270dc7e`, #5864): "generates" and the count of warnings. No script stops with an error.
  Each warning is of a class with a reason in the comments of #4037 (no new ticket): undefined constants (AoE2 DE
  reads 0 or skips them too, #5068, #5172), unknown objects with no public source (PR #5082), `no free tile` and
  `unknown land_id` (#4935), attributes that are not read yet (#3846), game modes (#4821), and `avoid_actor_area`
  in `real_world_manchuria` (its base scenario is only in the owner's install).

| Map | Script | Own generator | State |
|---|---|---|---|
| Acclivity | `Acclivity.rms` | no | generates, 2 warnings |
| Acropolis | `acropolis` | no | generates, 5 warnings |
| African Clearing | `AfricanClearing.rms` | no | generates, no warning |
| Aftermath | `Aftermath.rms` | no | generates, 15 warnings |
| Alpine Lakes | `Alpine_Lakes.rms` | no | generates, no warning |
| Amazon Tunnel | `AmazonTunnel.rms` | no | generates, 2 warnings |
| Aquarena | `Aquarena.rms` | no | generates, 17 warnings |
| Arabia | `Arabia.rms` | yes | generates, 12 warnings |
| Archipelago | `Archipelago.rms` | no | generates, 1 warning |
| Arena | `Arena.rms` | yes | generates, 17 warnings |
| Atacama | `Atacama.rms` | no | generates, 2 warnings |
| Baltic | `Baltic.rms` | no | generates, 10 warnings |
| Black Forest | `Black_Forest.rms` | yes | generates, 20 warnings |
| Bog Islands | `Bog_Islands.rms` | no | generates, 1 warning |
| Bogland | `Bogland.rms` | no | generates, 10 warnings |
| Border Dispute | `Border Dispute.rms` | no | generates, 18 warnings |
| BR Battle On Ice | `BR_BattleontheIce.rms` | no | generates, 26 warnings |
| BR El Dorado | `BR_ElDorado.rms` | no | generates, 5 warnings |
| BR Fall of Axum | `BR_FallofAxum.rms` | no | generates, 28 warnings |
| BR Fall of Rome | `BR_FallofRome.rms` | no | generates, 31 warnings |
| BR Majapahit Empire | `BR_TheMajapahitEmpire.rms` | no | generates, 11 warnings |
| Budapest | `budapest` | no | generates, 1 warning |
| Cenotes | `cenotes` | no | generates, 9 warnings |
| Chaos Pit | `Chaos Pit.rms` | no | generates, 16 warnings |
| City of Lakes | `cityoflakes` | no | generates, 3 warnings |
| Cliffbound | `Cliffbound.rms` | no | generates, 9 warnings |
| Coastal | `Coastal.rms` | no | generates, 17 warnings |
| Coastal Forest | `CoastalForest.rms` | no | generates, 17 warnings |
| Continental | `Continental.rms` | no | generates, no warning |
| Crater | `Crater.rms` | no | generates, no warning |
| Crater Lake | `Crater_Lake.rms` | no | generates, 1 warning |
| Crossroads | `Crossroads.rms` | no | generates, 1 warning |
| Crownwood | `Crownwood.rms` | no | generates, 14 warnings |
| CtR Monsoon | `CtR Monsoon` | no | generates, 5 warnings |
| CtR Pyramid Descent | `CtR Pyramid Descent` | no | generates, 5 warnings |
| CtR Random | `CtR Random` | no | generates, 5 warnings |
| CtR Spiral | `CtR Spiral` | no | generates, 5 warnings |
| Dorothea Quarry | `Dorothea Quarry.rms` | no | generates, 13 warnings |
| Dunesprings | `Dunesprings.rms` | no | generates, 7 warnings |
| Enclosed | `Enclosed.rms` | no | generates, 4 warnings |
| Eruption | `Eruption.rms` | no | generates, 3 warnings |
| Fortified Clearing | `fortified_clearing.rms` | no | generates, 23 warnings |
| Fortress | `Fortress.rms` | no | generates, 3 warnings |
| Four Lakes | `FourLakes.rms` | no | generates, no warning |
| Frigid Lake | `FrigidLake.rms` | no | generates, 5 warnings |
| Ghost Lake | `Ghost_Lake.rms` | no | generates, no warning |
| Glacis | `Glacis.rms` | no | generates, 19 warnings |
| Glade | `Glade.rms` | no | generates, 17 warnings |
| Gold Rush | `Gold_Rush.rms` | yes | generates, 1 warning |
| Golden Pit | `goldenpit` | no | generates, 1 warning |
| Golden Stream | `Golden_Stream.rms` | no | generates, 3 warnings |
| Golden Swamp | `GoldenSwamp.rms` | no | generates, no warning |
| Graupel | `Graupel.rms` | no | generates, 9 warnings |
| Greenland | `Greenland.rms` | no | generates, 10 warnings |
| Haboob | `Haboob.rms` | no | generates, 11 warnings |
| Hamburger | `hamburger` | no | generates, no warning |
| Hengehold | `Hengehold.rms` | no | generates, 13 warnings |
| Hideout | `hideout` | no | generates, 1 warning |
| Highland | `Highland.rms` | yes | generates, 5 warnings |
| Hill Fort | `hillfort` | no | generates, no warning |
| Hollow Woodlands | `Hollow_Woodlands.rms` | no | generates, 1 warning |
| Islands | `Islands.rms` | yes | generates, 1 warning |
| Isthmus | `Isthmus.rms` | no | generates, 12 warnings |
| Karsts | `Karsts.rms` | no | generates, 5 warnings |
| Kawasan | `Kawasan.rms` | no | generates, 16 warnings |
| Kilimanjaro | `Kilimanjaro.rms` | no | generates, 14 warnings |
| Land Madness | `LandMadness.rms` | no | generates, 3 warnings |
| Land Nomad | `LandNomad.rms` | no | generates, 12 warnings |
| Lombardia | `lombardia` | no | generates, 2 warnings |
| Lowland | `Lowland.rms` | no | generates, 8 warnings |
| Mangrove Jungle | `Mangrove_Jungle.rms` | no | generates, no warning |
| Marketplace | `Marketplace.rms` | no | generates, 4 warnings |
| Meadow | `Meadow.rms` | no | generates, 2 warnings |
| Mediterranean | `Mediterranean.rms` | yes | generates, 1 warning |
| MegaRandom | `Megarandom` | no | generates, 2 warnings |
| Michi | `Michi.rms` | no | generates, no warning |
| Migration | `Migration.rms` | no | generates, 16 warnings |
| Mongolia | `Mongolia.rms` | no | generates, 13 warnings |
| Morass | `Morass.rms` | no | generates, 2 warnings |
| Mountain Dunes | `Mountain_Dunes.rms` | no | generates, 8 warnings |
| Mountain Pass | `Mountain Pass.rms` | no | generates, 11 warnings |
| Mountain Range | `MountainRange.rms` | no | generates, 2 warnings |
| Mountain Ridge | `Mountain_Ridge.rms` | no | generates, no warning |
| Nile Delta | `Nile Delta.rms` | no | generates, no warning |
| Nomad | `nomad.rms` | yes | generates, 11 warnings |
| Northern Isles | `NorthernIsles.rms` | no | generates, 5 warnings |
| Oasis | `Oasis.rms` | no | generates, 13 warnings |
| Pacific Islands | `Pacific_Islands.rms` | no | generates, no warning |
| Ravines | `Ravines.rms` | no | generates, no warning |
| Ring Fortress | `RingFortress.rms` | no | generates, 17 warnings |
| River Divide | `River_Divide.rms` | no | generates, 7 warnings |
| Rivers | `Rivers.rms` | no | generates, 1 warning |
| Runestones | `Runestones.rms` | no | generates, 18 warnings |
| Sacred Springs | `SacredSprings.rms` | no | generates, 8 warnings |
| Salt Marsh | `Salt_Marsh.rms` | no | generates, no warning |
| Sandbank | `Sandbank.rms` | no | generates, no warning |
| Sandrift | `Sandrift.rms` | no | generates, 6 warnings |
| Scandinavia | `Scandanavia.rms` | no | generates, 20 warnings |
| Seize The Mountain | `SeizeTheMountain.rms` | no | generates, 5 warnings |
| Serengeti | `Serengeti.rms` | no | generates, no warning |
| Shoals | `Shoals.rms` | no | generates, 8 warnings |
| Shrubland | `Shrubland.rms` | no | generates, 17 warnings |
| Socotra | `Socotra.rms` | no | generates, 3 warnings |
| Steppe | `steppe` | no | generates, 15 warnings |
| Team Islands | `Team_Islands.rms` | no | generates, 19 warnings |
| Team Moats | `TeamMoats.rms` | no | generates, no warning |
| The Passage | `The_Passage.rms` | no | generates, 14 warnings |
| Valley | `valley` | no | generates, 3 warnings |
| Volcanic Island | `VolcanicIsland.rms` | no | generates, no warning |
| Wade | `Wade.rms` | no | generates, 8 warnings |
| Water Nomad | `Water_Nomad.rms` | no | generates, no warning |
| Wolf Hill | `Wolf_Hill.rms` | no | generates, no warning |
| Yucatán | `Yucatan.rms` | no | generates, 8 warnings |

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
| `TEAM0_SIZE0`, `LESS_THAN_THREE_PLAYERS`, `LESS_THAN_FIVE_PLAYERS`, `LESS_THAN_SEVEN_PLAYERS`, `RANKED_MATCH`, `TOURNAMENT_VERSION`, `ESCALATION_MODE`, `MODE_TOGGLE`, `DYNAMIC_SIZE` (2 to 10) | none: the lobby defines `TEAMn_SIZEm` only for teams 1 to 4; the others are switches of the script authors | none | no (the lobby never defines them) | survey #5087; not in the guide |
| `AZUREMASKING`, `EXTREME_ELEVATION`, `LEGACY_CODE`, `LEGACY_RELICS`, `NOMAD_CASTLE`, `NOMAD_HERDABLE`, `NOMAD_SCATTERED`, `NOMAD_TREATY`, `NOMAD_UNIT`, `REGICIDE_*` variants, `SEASONS_ALLOWMUDDYSHALLOWS`, `EMPIRE_WARS_*` variants, `*_ALLOW_FEEDING`, `DEBUG_MODE`, `TERRAIN_DEBUGGING`, `GNR_*`, `*_CAA_*` | none: switches of the script authors | none | no (the lobby never defines them) | survey |

### Undefined constants in math (#5068)

`PLAYERn_ALLY_COUNT` and `MAPSCALE_SIDE` are not predefined. The DE scripts define them: `includes/helpers.inc`
defines `PLAYERn_ALLY_COUNT` (0 with `PLAYERn_TEAM0`, else team size − 1) only for the players in the game, and
`includes/scaling.inc` defines `MAPSCALE_SIDE` = `MAPSIZE_SIDE / 100`. Source: the owner's search of the game files and
of the Zetnus guide (the guide has neither word, #5068). AoE2 DE reads an undefined constant in math (`#const`, `rnd`,
`(...)`) as 0 with no error. `rmap.calc` does the same and `generate` warns once per word.

## Research: object groups and tile shuffling (#5251)

| Word | Meaning | `rmap` | Source |
|---|---|---|---|
| `create_object_group NAME { add_object TYPE PERCENT ... }` | A pool of object types in `<OBJECTS_GENERATION>`. A later `create_object NAME` places objects of the pool (for example all cow variants as `HERDABLE_A`). AoE2 DE ignores the percent: each type of the pool has the same chance | `objects()`: each placed object draws a type of the pool; an `add_object` with an undefined object is skipped | aoe2-rms docs (docs.racket-lang.org/aoe2-rms, "create-object-group", "add-object") |
| `enable_tile_shuffling` (a `create_object` flag) | No public source found (web search, 2026-10-31). By its name: the candidate tiles in random order | read with no effect: `objects()` takes random free tiles already | none |

Owner decision (#3846, 2026-11-01): `enable_tile_shuffling` and `override_actor_radius_if_required` stay excluded.
They keep the warning "is not read yet". A run reads them only when a source of their effect is found.

The survey of #5087 also has `create_object: grouping` and `set_loose` (2 maps): no DE attribute has these names (the
attribute is `set_loose_grouping`). The warnings stay.
