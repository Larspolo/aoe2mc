# The achievements of AoE2 DE (#5278, epic #5277)

Source: the Steam achievement list of Age of Empires II: Definitive Edition (app 813780),
<https://steamcommunity.com/stats/813780/achievements>, read on 2026-10-31: 370 achievements (base game and DLCs).

In scope: the lines of `data/achievements.jsonl` (the advancement tab "Age of Empires II" of the datapack,
`aoe2mc.advancement_files`). The game program grants them by the key `event` (a later ticket of the epic).

- AoE2 DE has no achievement for the Castle Age or the Imperial Age. "Family Feudal" is the only age achievement
  (AoE2 DE: "Advance to the Feudal Age in a Campaign Scenario"; here: in any game).
- Counts (#5628): Minecraft keeps the advancements and the statistics per world, and each converted scenario is a new
  world. A count is in scope when the games of one world can reach it, so when one game can reach it (#5280).
  `AGE_OF_EMPIRES` of `data/achievements.jsonl` (win with every civilization) needs the wins of many worlds: it has
  no grant by the same rule.
- The six AI rows: the Steam text is cut after "on". The levels are the AoE2 DE "AI difficulty" names (Easiest,
  Standard, Moderate, Hard, Hardest, Extreme; `game/data/difficulty.jsonl`). The key `EASY_AI` is Standard.

The reasons of the `out` rows (the game program has no such event):

- `out: campaign`: a campaign, a mission of a campaign or a historical battle.
- `out: Return of Rome`: aoe2mc has no Return of Rome civilizations or campaigns.
- `out: no civilization`: "Indian Victory": the Indians civilization is now split (no key in `game/data/civs.jsonl`).
- `out: online`: the count of human players of an online lobby.
- `out: many games`: a count that one game cannot reach (see "Counts").
- `out: no event`: the unit, the ability or the count of the achievement is not in the game program.

The `in` rows give the event that they need. The new `in` rows (#5628) have no line in `data/achievements.jsonl` yet,
by event kind (one sub-issue of the epic per kind):

- build: `ACHIEVEMENT_STEPPE_PEOPLE`, `ACHIEVEMENT_SURVEILLANCE_NETWORK`
- kill: `ACHIEVEMENT_CASTLE_OF_DOUBT`, `ACHIEVEMENT_DARK_HUMOR`, `ACHIEVEMENT_FINAL_COUNTDOWN`, `ACHIEVEMENT_ITS_A_TREB`, `ACHIEVEMENT_KING_OF_THE_SEAS`, `ACHIEVEMENT_PROMACHOS`, `ACHIEVEMENT_SHUING_ENEMIES`
- policy: `ACHIEVEMENT_POLITICAL_ANIMAL`
- research: `ACHIEVEMENT_BY_AHURAMAZDAS_GRACE`, `ACHIEVEMENT_FLEMISH_REVOLUTION`
- train: `ACHIEVEMENT_BABY_BOOMER`
- win: `ACHIEVEMENT_HOMELESS`, `ACHIEVEMENT_SUPREMELY_UNEXPECTED`, `ACHIEVEMENT_WINGMAN`

| Steam key | Name | Description | Scope |
|---|---|---|---|
| AZTEC_VICTORY | Aztec Victory | Win a game playing as the Aztecs. | in |
| BERBERS_VICTORY | Berber Victory | Win a game playing as the Berbers. | in |
| BRITONS_VICTORY | Briton Victory | Win a game playing as the Britons. | in |
| BULGARIANS_VICTORY | Bulgarian Victory | Win a game playing as the Bulgarians. | in |
| BURMESE_VICTORY | Burmese Victory | Win a game playing as the Burmese. | in |
| BYZANTINES_VICTORY | Byzantine Victory | Win a game playing as the Byzantines. | in |
| CELTS_VICTORY | Celtic Victory | Win a game playing as the Celts. | in |
| CHINESE_VICTORY | Chinese Victory | Win a game playing as the Chinese. | in |
| CUMANS_VICTORY | Cuman Victory | Win a game playing as the Cumans. | in |
| ETHIOPIANS_VICTORY | Ethiopian Victory | Win a game playing as the Ethiopians. | in |
| FRANKS_VICTORY | Frankish Victory | Win a game playing as the Franks. | in |
| GOTHS_VICTORY | Gothic Victory | Win a game playing as the Goths. | in |
| HUNS_VICTORY | Hunnic Victory | Win a game playing as the Huns. | in |
| INCAS_VICTORY | Inca Victory | Win a game playing as the Incas. | in |
| INDIANS_VICTORY | Hindustani Victory | Won a game playing as the Hindustanis. | out: no civilization |
| ITALIANS_VICTORY | Italian Victory | Win a game playing as the Italians. | in |
| JAPANESE_VICTORY | Japanese Victory | Win a game playing as the Japanese. | in |
| KHMER_VICTORY | Khmer Victory | Win a game playing as the Khmer. | in |
| KOREANS_VICTORY | Korean Victory | Win a game playing as the Koreans. | in |
| MAGYARS_VICTORY | Magyar Victory | Win a game playing as the Magyars. | in |
| MALAY_VICTORY | Malay Victory | Win a game playing as the Malay. | in |
| MALIANS_VICTORY | Malian Victory | Win a game playing as the Malians. | in |
| MAYANS_VICTORY | Mayan Victory | Win a game playing as the Mayans. | in |
| MONGOLS_VICTORY | Mongol Victory | Win a game playing as the Mongols. | in |
| PERSIANS_VICTORY | Persian Victory | Win a game playing as the Persians. | in |
| PORTUGUESE_VICTORY | Portuguese Victory | Win a game playing as the Portuguese. | in |
| SARACENS_VICTORY | Saracen Victory | Win a game playing as the Saracens. | in |
| SLAVS_VICTORY | Slavic Victory | Win a game playing as the Slavs. | in |
| SPANISH_VICTORY | Spanish Victory | Win a game playing as the Spanish. | in |
| TATARS_VICTORY | Tatar Victory | Win a game playing as the Tatars. | in |
| TEUTONS_VICTORY | Teutonic Victory | Win a game playing as the Teutons. | in |
| TURKS_VICTORY | Turkish Victory | Win a game playing as the Turks. | in |
| VIETNAMESE_VICTORY | Vietnamese Victory | Win a game playing as the Vietnamese. | in |
| VIKINGS_VICTORY | Viking Victory | Win a game playing as the Vikings. | in |
| ACHIEVEMENT_CAMPAIGN_WALLACE_COMPLETED | Guardian of Scotland | Complete the William Wallace Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_JOANARC_COMPLETED | Iron Maid | Complete the Joan of Arc Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_SALADIN_COMPLETED | Custodian of the Holy Land | Complete the Saladin Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_KHAN_COMPLETED | For the Horde! | Complete the Genghis Khan Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_BARBAROSSA_COMPLETED | The Emperor Strikes Back | Complete the Barbarossa Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_ATTILA_COMPLETED | Huney, I Shrunk the Romans | Complete the Attila the Hun Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_ELCID_COMPLETED | El Campeador | Complete the El Cid Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_MONTEZUMA_COMPLETED | Emperor of Tenochtitlan | Complete the Montezuma Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_ALARIC_COMPLETED | The Thicker the Hay, the Easier Mowed | Complete the Alaric Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_DRACULA_COMPLETED | Vladislav, Baby Don't Hurt Me | Complete the Dracula Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_BARI_COMPLETED | A Tale of One City | Complete the Bari Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_SFORZA_COMPLETED | Renaissance Man | Complete the Sforza Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_ELDORADO_COMPLETED | Earth Shaker | Complete the Pachacuti Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_PRITHVIRAJ_COMPLETED | The Blind Archer | Complete the Prithviraj Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_BERBER_COMPLETED | Master of the Maghreb | Complete the Tariq ibn Ziyad Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_MALIAN_COMPLETED | King of Africa | Complete the Sundjata Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_PORTUGUESE_COMPLETED | Age of Discovery | Complete the Francisco de Almeida Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_ETHIOPIAN_COMPLETED | Destroyer of Axum | Complete the Yodit Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_MALAY_COMPLETED | Island Hopper | Complete the Gajah Mada Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_KHMER_COMPLETED | King of the Just Laws | Complete the Suryavarman I Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_BURMESE_COMPLETED | Cakkavatti | Complete the Bayinnaung Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_VIETNAMESE_COMPLETED | Rebel with a Cause | Complete the Le Loi Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_TATAR_COMPLETED | Empire of the Steppes | Complete the Tamerlane Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_BULGARIAN_COMPLETED | The Cabbage King | Complete the Ivaylo Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_CUMAN_COMPLETED | Yes we Khan! | Complete the Kotyan Khan Campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_HISTORICAL_BATTLES_COMPLETE | Battle Beast | Complete all Historical Battles in single player. | out: campaign |
| ACHIEVEMENT_WOLOLO | Wololo | Convert 1,000 units. | out: many games |
| ACHIEVEMENT_UNEXPECTED | Unexpected | Convert 100 units using Spanish Missionaries. | out: many games |
| ACHIEVEMENT_LOSING_YOUR_RELIGION | Losing Your Religion | Convert an enemy Monk. | in: convert an enemy MONK |
| ACHIEVEMENT_CHAIN_REACTION | Chain Reaction | Blow up an enemy Demolition Ship with a Demolition Ship of your own. | in: kill DEMOLITION_SHIP by DEMOLITION_SHIP |
| ACHIEVEMENT_KABOOM | Kaboom | Kill 1,000 enemy units using Demolition Ships. | out: many games |
| ACHIEVEMENT_BULLS_EYE | Bull's Eye | Destroy a Trebuchet with another Trebuchet. | in: kill TREBUCHET by TREBUCHET |
| ACHIEVEMENT_NO_WONDER_LEFT_BEHIND | The Wonder, the Wonder, the...Oh, Never Mind | Prevent the Korean Wonder from being destroyed in the | out: campaign |
| ACHIEVEMENT_CATHEDRAL_RUSH | A Truly Holy Emperor | Convert the Cathedral in Milan without acquiring a single Villager in the third Barbarossa mission | out: campaign |
| ACHIEVEMENT_NO_WONDER_ON_MY_WATCH | No Wonder on my Watch | Destroy every enemy Wonder before it is completed in the sixth Attila the Hun mission | out: campaign |
| ACHIEVEMENT_DIPLOMACY_IS_FOR_THE_MEEK | Diplomacy is for the Meek | Kill the Scythian Prince and defeat the Scythians in the first Attila the Hun mission | out: campaign |
| ACHIEVEMENT_KUSHLUK_ASSASSINATION | The Kushluk Assassination | Kill Kushluk before 20 minutes have elapsed in the second Genghis Khan mission | out: campaign |
| ACHIEVEMENT_I_WAS_IN_CHINA_BEFORE | I Was in China Before | Defeat the Jin before they start constructing a Wonder in the third Genghis Khan mission | out: campaign |
| ACHIEVEMENT_OFFENSE_IS_THE_BEST_DEFENSE | Offense Is the Best Defense | Defeat all opponents before constructing a Wonder in the sixth Saladin mission | out: campaign |
| ACHIEVEMENT_THE_GO_GETTER | The Go-Getter | Defeat the Hungarians before Subotai has arrived in the sixth Genghis Khan mission | out: campaign |
| ACHIEVEMENT_FUROR_TEUTONICUS | Furor Teutonicus | Defeat all opponents instead of collecting the required Relics in the first Barbarossa mission | out: campaign |
| ACHIEVEMENT_ATTILA_SPEED_RUN | Truly Countless Bodies | Defeat all opponents before 30 minutes have elapsed in the fifth Attila the Hun mission | out: campaign |
| ACHIEVEMENT_HOT_N_SPICY | Hot \u0026 Spicy | Prevent Tabasco from being defeated in the third Montezuma mission | out: campaign |
| ACHIEVEMENT_BATTLESHIP | Battleship | Win the Historical Battle | out: campaign |
| ACHIEVEMENT_SURYAVARMAN_RELICS | Relic Hoarder | Collect all Relics on the map in the fifth Suryavarman mission | out: campaign |
| ACHIEVEMENT_THE_MISSIONARY | The Missionary | Collect all Relics in the first El Cid mission | out: campaign |
| ACHIEVEMENT_OTTOMAN_GLORY_SEEKER | Turkish Delight | Win | out: campaign |
| ACHIEVEMENT_NO_HOJO | Lone Warrior | Win | out: campaign |
| ACHIEVEMENT_FIRE_WITH_FIRE | Fire with Fire | Amass 10 Condottieri, 10 Genoese Crossbowmen, and 10 Bombard Cannons in the fifth Dracula mission | out: campaign |
| ACHIEVEMENT_DESTROY_DELHI | Raging Wildfire | Conquer Delhi at least 5 minutes before the timer expires in the fourth Tamerlane mission | out: campaign |
| ACHIEVEMENT_KILL_KING_TAKAYUTPI | Chasing the Crown | Kill King Takayutpi before 5 minutes have elapsed in the first Bayinnaung mission | out: campaign |
| ACHIEVEMENT_NO_KILLING_PORTUGUESE | Friends, Countrymen, Lend Me Your Ears | Convert Afonso de Albuquerque without killing a single Portuguese unit in the fifth Francisco de Almeida mission | out: campaign |
| ACHIEVEMENT_NUMBERS_BEAT_EVERYTHING | Numerous As the Grains of Sand | Win the second Alaric mission | out: campaign |
| ACHIEVEMENT_ALARIC_SPEED_RUN | Rome Was Destroyed in One Day | Destroy all Roman Castles before 30 minutes have elapsed in the fourth Alaric mission | out: campaign |
| ACHIEVEMENT_DRAGON_SHIPS | Smoke on the Water | Purchase 20 Dragon Ships in the Historical Battle | out: campaign |
| ACHIEVEMENT_100_GBETO | With the Help of My Sisters | Amass an army of at least 100 Gbeto Warriors in the fourth Sundjata mission | out: campaign |
| ACHIEVEMENT_SATANS_MAP | Roar like a Lion | Win the fifth Sundjata mission | out: campaign |
| ACHIEVEMENT_NO_SUPPORT | An Army Marches on Its Stomach | Complete all secondary objectives and destroy all of Dagnajan's smaller bases before Dagnajan and his army march in the third Yodit mission | out: campaign |
| ACHIEVEMENT_RUSH_TO_THE_KING | No Royal Hair Touched | Reach the King before 10 minutes have elapsed in the second Gajah Mada mission | out: campaign |
| ACHIEVEMENT_NOT_THE_VIPER | Not a Greek Tragedy | Win without losing any of your four heroes in the fifth Le Loi mission | out: campaign |
| ACHIEVEMENT_NO_CASTLE_AGE | Cuman Flush | Win the second Kotyan mission | out: campaign |
| ACHIEVEMENT_DEFEAT_AUSTRIAN_DUKE | He Won't Be Back | Assist King Bela and defeat the Austrian Duke Frederick in the fifth Kotyan mission | out: campaign |
| ACHIEVEMENT_NO_WALLS | Pitched Battle | Successfully defend Cuzco without constructing any new walls or gates in the second Pachacuti mission | out: campaign |
| ACHIEVEMENT_D_DAY | D-Day (D stands for Demo) | Destroy an enemy Transport Ship with a Demolition Ship. | in: kill TRANSPORT_SHIP by DEMOLITION_SHIP |
| ACHIEVEMENT_ETERNAL_GRATITUDE | Eternal Gratitude | Encounter a Penguin in the Historical Battle | out: campaign |
| ACHIEVEMENT_ITS_A_TREB | It's a Treb! | Kill 25 units with Trebuchets. | in: count kill by TREBUCHET (25) |
| ACHIEVEMENT_MANGO_SHOTS | Mango Shots | Kill 500 units with Mangonels. | out: many games |
| ACHEVEMENT_HUN_WHAT_ARE_YOU_DOING | Hun, What Are You doing? | Burn down 200 buildings with Tarkans. | out: many games |
| ACHIEVEMENT_KNOCKING_ON_YOUR_DOOR | Knocking On Your Door | Demolish 200 buildings with Battering Rams. | out: many games |
| ACHIEVEMENT_CASTLE_CRUSHER | Castle Crusher | Destroy 50 Castles. | out: many games |
| ACHIEVEMENT_OUT_WITH_A_BANG | Out With a Bang | Kill an enemy King with a Petard or Demolition Ship. | in: kill KING by PETARD or DEMOLITION_SHIP |
| LITHUANIANS_VICTORY | Lithuanian Victory | Win a game playing as the Lithuanians. | in |
| ACHIEVEMENT_KARAMBOLAGE | Karambolage | Spam the enemy with 500 Karambit Warriors in a single game. | in |
| ACHIEVEMENT_ELEPHANTASTIC | Elephantastic | Train 40 War or Battle Elephants in a single game. | in |
| ACHIEVEMENT_FIGHTING_FROM_AFAR | Fighting From Afar | Create 500 Longbowmen in a single match. | in |
| ACHIEVEMENT_90_KG | 90kg Over 300 Meters | Build 300 Trebuchets. | out: many games |
| ACHIEVEMENT_FRANKLY_MY_DEAR | Frankly My Dear... | Create 100 Throwing Axemen in a single match. | in |
| ACHIEVEMENT_ANYONE_ORDER_PIZZA | Anyone Order a Pizza? | Train 1,000 Condottieri as a non-Italian civilization. | out: many games |
| ACHIEVEMENT_SUSHI_LOVER | Sushi Lover | Build 30 Japanese Fishing Ships. | in |
| ACHIEVEMENT_OUT_OF_THEIR_ELEMENT | Out of Their Element | Destroy a ship using a melee unit. | in: kill a ship by a melee unit |
| ACHIEVEMENT_CASTLE_OF_DOUBT | Castle of Doubt | Lose an unfinished Castle that is at least 95% complete. | in: lose a CASTLE site at 95 % or more |
| ACHIEVEMENT_THE_WONDER | The Wonder, the Wonder, Noooooo... | Build a Wonder. | in: build WONDER |
| ACHIEVEMENT_PLEASANT_PEASANT | Pleasant Peasant | Build 1,000 Farms in total. | out: many games |
| ACHIEVEMENT_SUPREMELY_UNEXPECTED | Supremely Unexpected | Win a match as the Spanish while only creating Villagers. | in: win as SPANISH with only VILLAGER trained |
| ACHIEVEMENT_LONG_LIVE_THE_KING | The King Is Dead, Long Live the King! | Win a Regicide game. | in |
| ACHIEVEMENT_MARCO_POLO | Marco Polo | Explore 99% of a ludicrously sized map. | in: explored 99 % of a Ludicrous map |
| ACHIEVEMENT_RELIC_HUNTER | Relic Hunter | Collect 100 Relics. | out: many games |
| ACHIEVEMENT_BIRD_SHOOTING | Bird Shooting | Kill an enemy Scout Cavalry with your Town Center. | in: kill SCOUT_CAVALRY by TOWN_CENTER |
| ACHIEVEMENT_DARK_DINNER | Dark Dinner | Eat 2 Wild Boars in the Dark Age. | in: gather 2 WILD_BOAR in the Dark Age |
| ACHIEVEMENT_DARK_HUMOR | Dark Humor | Kill 20 Villagers with Militia in the Dark Age. | in: count kill VILLAGER by MILITIA in the Dark Age (20) |
| ACHIEVEMENT_MASTERPIECE | Masterpiece | Win alone against 3 human opponents. | out: online |
| ACHIEVEMENT_FINAL_COUNTDOWN | Final Countdown | Destroy an opponent's Wonder with less than 100 years remaining on the Wonder Victory countdown. | in: kill a WONDER with less than 100 years of its countdown |
| ACHIEVEMENT_HOWDY_NEIGHBOR | Howdy Neighbor | Scale an enemy wall using a Siege Tower. | in: siege tower over an enemy wall |
| ACHIEVEMENT_TOO_LAME_TO_TAME | Too Lame To Tame | Loot 500 gold with Keshiks. | in: gold of KESHIK kills (500) |
| ACHIEVEMENT_EASIEST_AI | Rest in Peace | Beat an AI opponent on Easiest difficulty. | in: win against a bot on easiest |
| ACHIEVEMENT_MODERATE_AI | With Moderation | Beat an AI opponent on Moderate difficulty. | in: win against a bot on moderate |
| ACHIEVEMENT_HARD_AI | Rough Ride | Beat an AI opponent on Hard difficulty. | in: win against a bot on hard |
| ACHIEVEMENT_HARDEST_AI | Barbaric Manners | Beat an AI opponent on Hardest difficulty. | in: win against a bot on hardest |
| ACHIEVEMENT_EXTREME_AI | Prominent Player | Beat an AI opponent on Extreme difficulty. | in: win against a bot on extreme |
| ACHIEVEMENT_SHEEP_HOARDER | Sheep Hoarder | Gather 20 Sheep in a Random Map game. | in: gather 20 SHEEP |
| ACHIEVEMENT_HOMELESS | Homeless | Delete your starting Town Center and still win the game. | in: win after the delete of the own start TOWN_CENTER |
| ACHIEVEMENT_EASY_AI | Easy Going | Beat an AI opponent on Standard difficulty. | in: win against a bot on standard |
| ACHIEVEMENT_NO_SUNTZU_LIGHT | No Suntzu Light | Shoot 100,000 arrows with your Chu Ko Nu. | out: many games |
| ACHIEVEMENT_VICTORY_WITH_EVERY_CIV | Age of Empires | Win a game with every civilization. | in |
| ACHIEVEMENT_NOT_JUST_A_MILITIA | Not Just a Militia | Upgrade your Militia to Men-at-Arms | in: research MAN_AT_ARMS_UPGRADE |
| ACHIEVEMENT_FAMILY_FEUDAL | Family Feudal | Advance to the Feudal Age in a Campaign Scenario | in |
| ACHIEVEMENT_CAN_I_BE_FRANK_WITH_YOU | Can I be Frank with You? | Win the | out: campaign |
| ACHIEVEMENT_CHALLENGE_ACCEPTED | Challenge Accepted | Win any Medal in any Art of War Challenge | in: challenge medal |
| ACHIEVEMENT_GOING_FOR_THE_GOLD | Going for the Gold | Win a Gold Medal in any Art of War Challenge | in: challenge gold medal |
| ACHIEVEMENT_WINGMAN | Wingman | Win a Skirmish or Multiplayer Game with a Human or AI Teammate | in: win with an ally (--teams) |
| ACHIEVEMENT_BABY_BOOMER | Baby Boomer | Queue 5 Villagers at the Town Center in the Dark Age | in: queue 5 VILLAGER in the Dark Age |
| ACHIEVEMENT_BULL_MARKET | Bull Market | Create a Trade Route with another Market | in: trade route to another MARKET |
| ACHIEVEMENT_BON_VOYAGE | Bon Voyage | Turn on Auto-Scout in any Game Mode | in: autoscout on |
| ACHIEVEMENT_PREPARE_FOR_BOAR | Prepare for Boar! | Research Loom at the Town Center | in: research LOOM |
| ACHIEVEMENT_CAMPAIGN_BRITONS_COMPLETED | The English Justinian | Complete the Edward Longshanks campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_BURGUNDIANS_COMPLETED | The Good, the Bold, and the Fearless | Complete the Grand Dukes of the West campaign. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_SICILIANS_COMPLETED | Haute Culture | Complete the Hautevilles campaign. | out: campaign |
| ACHIEVEMENT_UNCHIVALROUS_PRAGMATIST | Unchivalrous Pragmatist | Defeat Simon the Younger's army before the baronial forces attack in | out: campaign |
| ACHIEVEMENT_THRONE_THIEF | Throne Thief | Steal the Stone of Scone in the fourth Edward Longshanks mission | out: campaign |
| ACHIEVEMENT_MALLEUS_SCOTORUM | Malleus Scotorum | Kill William Wallace before Robert the Bruce betrays you in | out: campaign |
| ACHIEVEMENT_NO_WHEELS | No Wheels | Do not construct a single siege weapon in the mission | out: campaign |
| ACHIEVEMENT_A_SECOND_HASTINGS | A Second Hastings | Wipe out Humphrey's base before defeating Jacqueline in | out: campaign |
| ACHIEVEMENT_SHUT_UP_LA_HIRE | Shut Up La Hire! | Defeat the French army before capturing Joan of Arc in the mission | out: campaign |
| ACHIEVEMENT_SELFMADE_MAN | Self-Made Man | Win without allying with Argyrus or Guaimar in the mission | out: campaign |
| ACHIEVEMENT_HAUTE_HAUTE_BRIEF_CANDLE | Haute, Haute, brief candle! | Inspire a rebellion in the second Hautevilles mission | out: campaign |
| ACHIEVEMENT_ITALY_JONES_AND_THE_FIRST_CRUSADE | Italy Jones and the First Crusade | Do not lose a hero in the fourth Hautevilles mission | out: campaign |
| BURGUNDIANS_VICTORY | Burgundian Victory | Win a game playing as the Burgundians. | in |
| SICILIANS_VICTORY | Sicilian Victory | Win a game playing as the Sicilians. | in |
| ACHIEVEMENT_FLEMISH_REVOLUTION | Golden Spurs | Transform 50 Villagers by researching Flemish Revolution. | in: research FLEMISH_REVOLUTION (50 villagers) |
| ACHIEVEMENT_DONJON_SERJEANT | Tour d'Italie | Construct a Donjon and use it to train a Serjeant. | in: train SERJEANT at a DONJON |
| ACHIEVEMENT_CAMPAIGN_LITHUANIANS_COMPLETED | Bond of Brothers | Complete the Algirdas and Kestutis campaign. | out: campaign |
| ACHIEVEMENT_TOLERANT_PIETY | Tolerant Piety | Build a Monastery or Shrine in every Lithuanian village in | out: campaign |
| ACHIEVEMENT_SCATTERED_HORDE | Scattered Horde | Kill all enemy commanders before defeating their hordes in | out: campaign |
| ACHIEVEMENT_MINT_CONDITION | Mint Condition | Deliver the Ransom Cart undamaged in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_POLES_COMPLETED | Star of the Poles | Complete the Jadwiga campaign. | out: campaign |
| ACHIEVEMENT_PROTECTOR_REALM | Protector of the Realm | Win without losing any neutral towns to Halych in | out: campaign |
| ACHIEVEMENT_NO_BAGGAGE | No Baggage | Defeat the Crimean Tatars without building a Town Center in | out: campaign |
| ACHIEVEMENT_NO_QUARTER | No Quarter | Kill Ulrich von Jungingen and Nicolas von Renys in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_BOHEMIANS_COMPLETED | Man of the Chalice | Complete the Jan Zizka campaign. | out: campaign |
| ACHIEVEMENT_MALEVOLENT_MARAUDER | Malevolent Marauder | Destroy all 6 Bohemian villages in | out: campaign |
| ACHIEVEMENT_ZIZKOV_HILL | Zizkov Hill | Do not lose the Old Tower northeast of your city in | out: campaign |
| ACHIEVEMENT_AGAINST_ALL | Against All | Defeat the Crusaders in the fifth Jan Zizka mission | out: campaign |
| BOHEMIANS_VICTORY | Bohemian Victory | Win a game playing as the Bohemians. | in |
| POLES_VICTORY | Polish Victory | Win a game playing as the Poles. | in |
| ACHIEVEMENT_OOF_NICE | Rhapsody of the Bohemians | Train 10 Houfnices as the Bohemians. | in |
| ACHIEVEMENT_FAST_FOOD | Fast Food | Gather 500 food by constructing farms next to Folwarks as the Poles. | in: gather 500 food from farms at a FOLWARK as POLES |
| ACHIEVEMENT_CAMPAIGN_HINDUSTANIS_COMPLETED | The Persian Tiger | Complete the Babur campaign. | out: campaign |
| ACHIEVEMENT_NEVER_TRUST | Never Trust a Campaign AI | Ignore Kabul's offer to form a non-aggression pact in | out: campaign |
| ACHIEVEMENT_AN_OFFER | An Offer You Khan't Refuse | Convert both Alam Khan and Daulat Khan in | out: campaign |
| ACHIEVEMENT_THE_RENOVATOR | The Renovator | Repair all 4 Town Centers in the devastated villages in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_DRAVIDIANS_COMPLETED | Like Father, Like Son | Complete the Rajendra campaign. | out: campaign |
| ACHIEVEMENT_NO_REST_FOR_THE_WICKED | No Rest for the Wicked | Defeat Mannaram and Polonnaruwa without capturing a Town Center in Rajendra #2. | out: campaign |
| ACHIEVEMENT_EYE_OF_THE_TIGER | Eye of the Tiger | Defeat Srivijaya, Madurai, the Chalukyan Empire and the Pirates in Rajendra 3. | out: campaign |
| ACHIEVEMENT_NO_WONDER_YOU_WON | No Wonder You Won | Win the game before Mahipala completes his Wonder in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_BENGALIS_COMPLETED | Won't You Take Me by the Hand | Complete the Devapala campaign. | out: campaign |
| ACHIEVEMENT_HUNA_JOIN_ME | Huna Join Me? | Convert all 3 Huna Khans in | out: campaign |
| ACHIEVEMENT_CONSTRUCTION_CANCELLATION | Construction Cancellation | Destroy the Rashtrakuta Wonder before it is completed in | out: campaign |
| ACHIEVEMENT_PARINIRVANA | Parinirvana | Accumulate 100 piety points in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_RAJA_OF_THE_PEOPLE | Raja of the People | Save both allied villages in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_HOPELESS_ROMANTIC | Hopeless Romantic | Win | out: campaign |
| ACHIEVEMENT_CAMPAIGN_INSPIRING_POET | Inspiring Poet | Convert all Rajas before the Ghorids attack in Prithviraj #5 on Hard difficulty. | out: campaign |
| BENGALIS_VICTORY | Bengali Victory | Win a game playing as the Bengalis. | in |
| DRAVIDIANS_VICTORY | Dravidian Victory | Win a game playing as the Dravidians. | in |
| GURJARAS_VICTORY | Gurjara Victory | Win a game playing as the Gurjaras. | in |
| ACHIEVEMENT_FACE_MY_RATHA | Face My Ratha | Train 10 Rathas as the Bengalis. | in |
| ACHIEVEMENT_KING_OF_THE_SEAS | King of the Seas | Sink 10 enemy ships with Thirisadais as the Dravidians. | in: count kill ship by THIRISADAI as DRAVIDIANS (10) |
| ACHIEVEMENT_FORGED_IN_THE_HEAT_OF_BATTLE | Forged in the Heat of Battle | Train 10 Chakram Throwers as the Gurjaras. | in |
| ACHIEVEMENT_CAMPAIGN_SUMERIANS_COMPLETED | The God of War | Complete the Sargon campaign. | out: campaign |
| ACHIEVEMENT_NOT_CUTTING_CORNERS | Not Cutting Corners | Subdue both Sippar and Borsippa in | out: campaign |
| ACHIEVEMENT_EXPEDITED_DELIVERY | Expedited Delivery | Bring the Artifact to each city-state before 30 minutes have elapsed in | out: campaign |
| ACHIEVEMENT_UR_OUT_OF_HERE | Ur Out of Here | Destroy Ur's Wonder before it is completed in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_MACEDONIANS_COMPLETED | Back to Square One | Complete the Pyrrhus campaign. | out: campaign |
| ACHIEVEMENT_WHAT_WOULD_ALEXANDER_HAVE_DONE | What Would Alexander Have Done? | Win with all allied Town Centers remaining in | out: campaign |
| ACHIEVEMENT_GREECED_LIGHTNING | Greece'd Lightning | Win before Demetrius arrives in | out: campaign |
| ACHIEVEMENT_THE_BEST_DEFENSE | The Best Defense... | Defeat all enemies in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_ROMANS_COMPLETED | Optimus Princeps | Complete the Trajan campaign. | out: campaign |
| ACHIEVEMENT_ARE_YOU_NOT_ENTERTAINED | Are You Not Entertained? | Win | out: campaign |
| ACHIEVEMENT_I_AM_LEGION | I Am Legion | Defeat the Dacian Army in | out: campaign |
| ACHIEVEMENT_YOU_HAVE_NO_POWER_HERE | You Have No Power Here! | Lose less than 5 units to conversion in | out: campaign |
| ROMAN_VICTORY | Roman Victory | Win a game as the Romans. | in |
| POMPEII_ASSYRIAN_VICTORY | Assyrian Victory | Win a game as the Assyrians in Return of Rome. | out: Return of Rome |
| POMPEII_BABYLONIAN_VICTORY | Babylonian Victory | Win a game as the Babylonians in Return of Rome. | out: Return of Rome |
| POMPEII_CARTHAGINIAN_VICTORY | Carthaginian Victory | Win a game as the Carthaginians in Return of Rome. | out: Return of Rome |
| POMPEII_CHOSON_VICTORY | Choson Victory | Win a game as the Choson in Return of Rome. | out: Return of Rome |
| POMPEII_EGYPTIAN_VICTORY | Egyptian Victory | Win a game as the Egyptians in Return of Rome. | out: Return of Rome |
| POMPEII_GREEK_VICTORY | Greek Victory | Win a game as the Greeks in Return of Rome. | out: Return of Rome |
| POMPEII_HITTITE_VICTORY | Hittite Victory | Win a game as the Hittites in Return of Rome. | out: Return of Rome |
| POMPEII_LACVIET_VICTORY | Lac Viet Victory | Win a game as the Lac Viet in Return of Rome | out: Return of Rome |
| POMPEII_MACEDONIAN_VICTORY | Macedonian Victory | Win a game as the Macedonians in Return of Rome. | out: Return of Rome |
| POMPEII_MINOAN_VICTORY | Minoan Victory | Win a game as the Minoans in Return of Rome. | out: Return of Rome |
| POMPEII_PALMYRAN_VICTORY | Palmyran Victory | Win a game as the Palmyrans in Return of Rome. | out: Return of Rome |
| POMPEII_PERSIAN_VICTORY | Persian Victory | Win a game as the Persians in Return of Rome. | out: Return of Rome |
| POMPEII_PHOENICIAN_VICTORY | Phoenician Victory | Win a game as the Phoenicians in Return of Rome. | out: Return of Rome |
| POMPEII_ROMAN_VICTORY | Roman Victory | Win a game as the Romans in Return of Rome. | out: Return of Rome |
| POMPEII_SHANG_VICTORY | Shang Victory | Win a game as the Shang in Return of Rome. | out: Return of Rome |
| POMPEII_SUMERIAN_VICTORY | Sumerian Victory | Win a game as the Sumerians in Return of Rome. | out: Return of Rome |
| POMPEII_YAMATO_VICTORY | Yamato Victory | Win a game as the Yamato in Return of Rome. | out: Return of Rome |
| ACHIEVEMENT_RIDE_FOR_RUIN | Ride for Ruin! | Kill 15 units with Scouts in the Tool Age in Return of Rome. | out: Return of Rome |
| ACHIEVEMENT_CALM_COOL_AND_COLLECTED | Calm, Cool, and Collected | Win 3 games in a row in Return of Rome. | out: Return of Rome |
| ACHIEVEMENT_AGILE_AS_A_SPARROW | Agile as a Sparrow | Win a game without losing a single unit in Return of Rome. | out: Return of Rome |
| ACHIEVEMENT_I_WONDER_WHY_I_DID_THAT | I Wonder Why I Did That? | Win a game by constructing a Wonder in Return of Rome. | out: Return of Rome |
| ACHIEVEMENT_FORGED_IN_IRON | Forged in Iron | Reach the Iron Age before 20 minutes of game time have elapsed in Return of Rome. | out: Return of Rome |
| ACHIEVEMENT_CHARIOTABLE_NUMBERS | Chariotable Numbers | Train 60 Chariot Archers in Return of Rome. | out: Return of Rome |
| ACHIEVEMENT_BUILDER_OF_CIVILIZATIONS | Builder of Civilizations | Complete the Ascent of Egypt campaign. | out: Return of Rome |
| ACHIEVEMENT_TACTICAL_RETREAT | Tactical Retreat | Complete The First Punic War campaign. | out: Return of Rome |
| ACHIEVEMENT_PHILHELLENE | Philhellene | Complete the Glory of Greece Campaign | out: Return of Rome |
| ACHIEVEMENT_LAW_MAKER | Law Maker | Complete the Voices of Babylon Campaign | out: Return of Rome |
| ACHIEVEMENT_CAMPAIGN_PERSIANS_COMPLETED | Call Me Ismail | Complete the Ismail campaign. | out: campaign |
| ACHIEVEMENT_SNEAK_ATTACK | Sneak Attack | Kill Farrukh Yasar before he reaches his fortress in | out: campaign |
| ACHIEVEMENT_LANDSLIDE | Landslide Election | Capture all Tabriz noblemen in | out: campaign |
| ACHIEVEMENT_NO_GUNS | I Ain't 'Fraid of No Guns | Defeat the Ottomans in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_ARMENIANS_COMPLETED | Lord of the Mountains | Complete the Thoros the Great campaign. | out: campaign |
| ACHIEVEMENT_BOUNTY_HUNTER | Bounty Hunter | Convert at least three Byzantine generals in | out: campaign |
| ACHIEVEMENT_RAIDING_PARTY | Raiding Party! | Defeat all enemy Cypriot players in | out: campaign |
| ACHIEVEMENT_CHURCH_SANCTUARY | Church Sanctuary | Do not lose any Tarsos Villagers in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_GEORGIANS_COMPLETED | Georgia On My Mind | Complete the Tamar campaign. | out: campaign |
| ACHIEVEMENT_GAME_OVER_YURY | Game's Over Yury | Defeat Yury before the end of the siege in | out: campaign |
| ACHIEVEMENT_AUNTIE_DEAREST | Auntie Dearest | Ensure Alexios completes his Wonder in | out: campaign |
| ACHIEVEMENT_ALEXANDRA_THE_GREAT | Alexandra the Great | Complete all side-quests in | out: campaign |
| ARMENIANS_VICTORY | Armenian Victory | Win a game playing as the Armenians. | in |
| GEORGIANS_VICTORY | Georgian Victory | Win a game playing as the Georgians. | in |
| ACHIEVEMENT_CAMPAIGN_HEROES_AND_VILLAINS_COMPLETED | Heroes and Villains | Complete all Victors and Vanquished scenarios on any difficulty. | out: campaign |
| ACHIEVEMENT_LOST_VIKINGS | Lost Vikings | Find three lost Vikings in | out: campaign |
| ACHIEVEMENT_THE_OLD_FASHIONED_WAY | The Old-fashioned Way | Win without constructing a Trebuchet in | out: campaign |
| ACHIEVEMENT_DAIMYO_OF_THE_NINE_PROVINCES | Daimyo of the Nine Provinces | Defeat the Shogun and conquer all Nine Provinces by 1600 CE in | out: campaign |
| ACHIEVEMENT_PLEBEIAN_PRESERVER | Plebeian Preserver | Do not lose a Villager in | out: campaign |
| ACHIEVEMENT_VANDALIZED | Vandalized | Sack Rome by 455 CE in | out: campaign |
| ACHIEVEMENT_UNITED_WE_FALL | United We Fall | Obtain four allies before the Mongols arrive in | out: campaign |
| ACHIEVEMENT_AGE_OF_VIKINGS | Age of Vikings | Find all Viking heroes in | out: campaign |
| ACHIEVEMENT_GENERATIONAL_AMBITIONS | Generational Ambitions | Achieve all of a leader's ambitions in | out: campaign |
| ACHIEVEMENT_BREAD_AND_CIRCUSES | Bread and Circuses | Support the winning chariot team in | out: campaign |
| ACHIEVEMENT_GALLEON_BLING | Galleon Bling | Capture a Spanish Galleon in | out: campaign |
| ACHIEVEMENT_SO_EPIC | So Epic | Complete all 50 Saga objectives in | out: campaign |
| ACHIEVEMENT_CIVIS_ROMANUS | Civis Romanus | Do not lose a city in | out: campaign |
| ACHIEVEMENT_SEEDS_OF_THEIR_OWN_DESTRUCTION | Seeds of Their Own Destruction | Win | out: campaign |
| ACHIEVEMENT_A_MOST_CONVENIENT_DEATH | A Most Convenient Death | Ensure Carloman dies in | out: campaign |
| ACHIEVEMENT_FASTER_THAN_A_SPEEDING_CANNONBALL | Faster Than a Speeding Cannonball | Kill Constantine XI and capture the Hagia Sophia before 15 May 1453 in | out: campaign |
| ACHIEVEMENT_TRUST_NO_ONE | Trust No One | Win | out: campaign |
| ACHIEVEMENT_COUP_DETAT | Coup D'état | Win | out: campaign |
| ACHIEVEMENT_SAXON_REVENGE | Saxon Revenge | Defeat West Francia in | out: campaign |
| ACHIEVEMENT_SHOGUN | Shogun | Win | out: campaign |
| ACHIEVEMENT_BUT_ITS_PROVOCATIVE | But It's Provocative | Provoke Fu Jian before he is ready in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_BATTLE_FOR_GREECE_COMPLETED | Nemesis | Finish the entire Chronicles: Battle for Greece campaign. | out: campaign |
| ACHIEVEMENT_ENTER_THE_EPIC | Enter the Epic | Complete | out: campaign |
| ACHIEVEMENT_LEADER_OF_MEN | Leader of Men | Attain all available aura upgrades in the Battle for Greece campaign. | out: campaign |
| ACHIEVEMENT_FIGHT_IN_THE_SHADE | Fight in the Shade | Survive at Thermopylae for 5 minutes after completing the main objective in | out: campaign |
| ACHIEVEMENT_FIRST_CITIZEN | First Citizen | Complete | out: campaign |
| ACHIEVEMENT_ALL_ACCOUNTED_FOR | All Accounted For | Do not lose a single resource cart in | out: campaign |
| ACHIEVEMENT_A_SUITABLE_SATRAP | A Suitable Satrap | Complete | out: campaign |
| ACHIEVEMENT_FRIEND_OF_ARTEMSIA | Friend of Artemisia | Assist Artemisia in both | out: campaign |
| ACHIEVEMENT_THE_GREAT_KINGS_WRATH | The Great King's Wrath | Defeat all enemy players in | out: campaign |
| ACHIEVEMENT_MARATHONOMACHOS | Marathonomachos | Find and complete all quests in | out: campaign |
| ACHIEVEMENT_ADMIRABLE_ADMIRAL | Admirable Admiral | Research all naval technologies in | out: campaign |
| ACHIEVEMENT_THUNDERING_ZEUS | Thundering Zeus! | Do not lose a single Market or Port in Byzantium during | out: campaign |
| ACHIEVEMENT_FRIEND_OF_THE_HELOTS | Friend of the Helots | Complete | out: campaign |
| ACHIEVEMENT_TOMB_RAIDER | Tomb Raider | Complete | out: campaign |
| ACHIEVEMENT_SACK_AND_BURN | Sack and Burn | Loot Notium, Priene, and the three cities specified by Cyrus in | out: campaign |
| ACHIEVEMENT_CRISIS_MANAGEMENT | Crisis Management | Complete | out: campaign |
| ACHIEVEMENT_BLOCKADE_BREAKER | Blockade Breaker | Destroy both naval blockades in | out: campaign |
| ACHIEVEMENT_PHILOLACON | Philolacon | Give a relic to the Spartans in both | out: campaign |
| ACHIEVEMENT_REJECT_THE_REGENT | Reject the Regent | Give a relic to Salamis in | out: campaign |
| ACHIEVEMENT_COMBINED_ARMS | Combined Arms | Complete | out: campaign |
| ACHIEVEMENT_BY_AHURAMAZDAS_GRACE | By Ahuramazda's Grace | Research an Achaemenid Town Center upgrade. | in: research ECONOMIC_TOWN_CENTER, DEFENSIVE_TOWN_CENTER or MILITARY_TOWN_CENTER |
| ACHIEVEMENT_POLITICAL_ANIMAL | Political Animal | Change your policy as the Athenians. | in: policy change as ATHENIANS |
| ACHIEVEMENT_PROMACHOS | Promachos | Kill 10 enemy units with a Spartan Polemarch. | in: count kill by POLEMARCH (10) |
| ACHAEMENIDS_VICTORY | Achaemenid Victory | Win a game playing as the Achaemenid in Chronicles: Battle for Greece. | in |
| ATHENIANS_VICTORY | Athenian Victory | Win a game playing as the Athenians in Chronicles: Battle for Greece. | in |
| SPARTANS_VICTORY | Spartan Victory | Win a game playing as the Spartans in Chronicles: Battle for Greece. | in |
| WEI_VICTORY | Wei Victory | Win a game playing as the Wei. | in |
| SHU_VICTORY | Shu Victory | Win a game playing as the Shu. | in |
| WU_VICTORY | Wu Victory | Win a game playing as the Wu. | in |
| ACHIEVEMENT_CAMPAIGN_SHU_COMPLETED | The Imperial Uncle | Complete the Liu Bei campaign. | out: campaign |
| ACHIEVEMENT_A_HERO_COMES | A Hero Comes; He Gains Renown | Use one of your heroes' active abilities in Liu Bei 1. | out: campaign |
| ACHIEVEMENT_AWAKEN_THE_DRAGON | Awaken the Dragon | Deploy Zhuge Liang's fire trap in Liu Bei 3. | out: campaign |
| ACHIEVEMENT_MAN_OF_THE_PEOPLE | Man of the People | Bring all Civilian Carriages to Sun Quan in Liu Bei 4. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_WEI_COMPLETED | Hero of Chaos | Complete the Cao Cao campaign. | out: campaign |
| ACHIEVEMENT_HORSES_FOR_COURSES | Horses for Courses | Train no military units aside from mounted units in Cao Cao 1. | out: campaign |
| ACHIEVEMENT_LIKE_TAKING_CANDY | Like Taking Candy From A Baby | Take Ye before defeating any of the brothers in Cao Cao 4. | out: campaign |
| ACHIEVEMENT_DO_NOT_PURSUE | Do Not Pursue Lü Bu | Defeat Lü Bu before 20 minutes have elapsed in Cao Cao 2. | out: campaign |
| ACHIEVEMENT_CAMPAIGN_WU_COMPLETED | King of the Southlands | Complete the Sun Clan campaign. | out: campaign |
| ACHIEVEMENT_THE_TIGER_OF_JIANGDONG | The Tiger of Jiangdong | Defeat Dong Zhuo's Raiders in Sun Clan 1. | out: campaign |
| ACHIEVEMENT_THE_LITTLE_CONQUEROR | The Little Conqueror | Defeat the White Tiger in Sun Clan 3. | out: campaign |
| ACHIEVEMENT_I_AM_COMING_FOR_YOU | I Am Coming For You, Liu Biao | Capture all Castles in Sun Clan 4. | out: campaign |
| ACHIEVEMENT_DRIVE_BY_BARRAGE | Drive-By Barrage | Build 20 War Chariots as the Shu. | in |
| ACHIEVEMENT_SHUING_ENEMIES | Shu'ing Enemies | Kill 50 units with White Feather Guards as the Shu. | in: count kill by WHITE_FEATHER_GUARD as SHU (50) |
| ACHIEVEMENT_TIME_FOR_A_RAISE | Time for a Raise | Fully promote 10 Tiger Cavalry as the Wei. | out: no event |
| ACHIEVEMENT_WEI_MARCH_ON_OUR_STOMACHS | Wei March on Our Stomachs | Generate 5000 food with Tuntian as the Wei. | in: gather 5000 food from TUNTIAN as WEI |
| ACHIEVEMENT_ACID_RAIN | Acid Rain | Destroy 20 buildings with Fire Archers as the Wu. | out: no event |
| ACHIEVEMENT_DARE_TO_DIE | Dare to Die | Re-equip 20 shields with Jian Swordsmen as the Wu. | out: no event |
| JURCHENS_VICTORY | Jurchens Victory | Win a game playing as the Jurchens. | in |
| KHITANS_VICTORY | Khitans Victory | Win a game playing as the Khitans. | in |
| ACHIEVEMENT_FIREWORKS_SHOW | Fireworks Show | Fire 100 projectiles with Rocket Carts. | out: no event |
| ACHIEVEMENT_IM_ON_FIRE | I'm On Fire... Fireball! | Kill 50 units with Fire Lancers' charged attacks. | out: no event |
| ACHIEVEMENT_I_AM_THE_STORM | I Am the Storm | Do 10000 damage with Grenadiers and Rocket Carts with Thunderclap Bombs researched as the Jurchens. | out: no event |
| ACHIEVEMENT_STEPPE_PEOPLE | Steppe People | Build 50 Pastures as the Khitans. | in: count build PASTURE as KHITANS (50) |
| ACHIEVEMENT_IRON_ARMY | Iron Army | Block 100 attacks with Iron Pagodas as the Jurchens. | out: no event |
| ACHIEVEMENT_MEDIEVAL_SLASHER | Medieval Slasher | Kill 50 units with Liao Daos as the Khitans. | out: no event |
| ACHIEVEMENT_CAMPAIGN_PROVIDENCE_COMPLETED | The Great | Finish the entire Chronicles: Alexander the Great campaign. | out: campaign |
| ACHIEVEMENT_MORE_DANGER_MORE_GLORY | More Danger, More Glory | Always side with Cleitus in | out: campaign |
| ACHIEVEMENT_BASILEUS | Basileus | Reach 100 Legitimacy in | out: campaign |
| ACHIEVEMENT_BLOOD_IN_THE_STREETS | Blood in the Streets | In | out: campaign |
| ACHIEVEMENT_AN_ARMY_MARCHES_ON_ITS_STOMACH | Supply Surplus | Gather the required resources in under 25 minutes in | out: campaign |
| ACHIEVEMENT_ALEXANDRIA_ESCHATE | Alexandria Eschate | Fully upgrade every district in | out: campaign |
| ACHIEVEMENT_AMPHIBIOUS_ASSAULT | Amphibious Assault | In | out: campaign |
| ACHIEVEMENT_CHOKEHOLD | Chokehold | Complete | out: campaign |
| ACHIEVEMENT_INDICA | Indica | Complete the Indica (discover all events) and gather all treasures in | out: campaign |
| ACHIEVEMENT_SING_GODDESS_THE_WRATH_OF_ALEXANDER | Sing, Goddess, the Wrath of Alexander | Defeat all 4 Cossaean Tribes in | out: campaign |
| MACEDONIAN_VICTORY | Macedonian Victory (Chronicles) | Win a game playing as the Macedonians in Chronicles: Alexander the Great. | in |
| THRACIAN_VICTORY | Thracian Victory | Win a game playing as the Thracians. | in |
| PURU_VICTORY | Puru Victory | Win a game playing as the Puru. | in |
| ACHIEVEMENT_CAMPAIGN_MAPUCHE_COMPLETED | Chile Con Carnage | Complete the Lautaro campaign. | out: campaign |
| ACHIEVEMENT_HOMELAND_INSECURITY | Homeland Insecurity | Always have at least three allied villages under your control in | out: campaign |
| ACHIEVEMENT_OUR_LITTLE_PONIES | Our Little Ponies | Bring all 25 horses to the allied corral in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_MUISCA_COMPLETED | Golden Paths | Complete the El Dorado campaign. | out: campaign |
| ACHIEVEMENT_TAKE_IRACA | One Does Not Simply Take Iraca | Do not allow your enemy to ever win the state of Iraca over to their side in | out: campaign |
| ACHIEVEMENT_EXPEDITION_IMPOSSIBLE | Expedition Impossible | Defeat Quesada's and Federmann's expeditions in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_TUPI_COMPLETED | Warden of the Jungle | Complete the Arariboia campaign. | out: campaign |
| ACHIEVEMENT_DYNAMITE_DELUXE | Dynamite Deluxe | Find and blow up all gunpowder barrels in | out: campaign |
| ACHIEVEMENT_TUPI_OR_NOT_TUPI | Tupi or not Tupi | Win the mission | out: campaign |
| MAPUCHE_VICTORY | Mapuche Victory | Win a game playing as the Mapuche. | in |
| MUISCA_VICTORY | Muisca Victory | Win a game playing as the Muisca. | in |
| TUPI_VICTORY | Tupi Victory | Win a game playing as the Tupi. | in |
| ACHIEVEMENT_SURVEILLANCE_NETWORK | Surveillance Network | Construct 10 Outposts with Champi Warriors. | in: count build OUTPOST by CHAMPI_WARRIOR (10) |
| ACHIEVEMENT_CAMPAIGN_HARALD1_COMPLETED | The Hero's Journey | Complete The Exiled Prince Campaign. | out: campaign |
| ACHIEVEMENT_THE_STUFF_OF_LEGEND | The Stuff of Legend | Complete every side quest related to defeating a Sicilian town in | out: campaign |
| ACHIEVEMENT_GANG_BACK_TOGETHER | Gettin' the Gang Back Together | Find all Varangian soldiers scattered throughout Constantinople in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_HARALD2_COMPLETED | Horned Helmet Tyrant | Complete The Hard Ruler Campaign. | out: campaign |
| ACHIEVEMENT_LEAVE_MAGNUS_ALONE | Leave Magnus Alone!! | Do not allow the enemy to destroy a single allied Dock in | out: campaign |
| ACHIEVEMENT_YOUR_GOD_NOW | I'm Your God Now | Pacify at least 2 jarldoms by placing a Relic in their Monasteries in | out: campaign |
| ACHIEVEMENT_CAMPAIGN_HARALD3_COMPLETED | Seven Feet of English Ground | Complete The Last Viking Campaign. | out: campaign |
| ACHIEVEMENT_GET_OUT_OF_MY_SWAMP | Get Out Of My Swamp! | Do not allow the enemy to ever capture the Monument in Riccall in | out: campaign |
| ACHIEVEMENT_HOARDRADA | Hoardrada | Play | out: campaign |
| SAXONS_VICTORY | Saxons Victory | Win a game playing as the Saxons. | in |
| VARANGIANS_VICTORY | Varangians Victory | Win a game playing as the Varangians. | in |
| DANES_VICTORY | Danes Victory | Win a game playing as the Danes. | in |
| ACHIEVEMENT_MURDER_FOR_HIRE | Murder for Hire | Accumulate 10000 gold using Varangian Guards. | out: no event |
