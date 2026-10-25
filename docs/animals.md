# Animals

Each AoE2 animal becomes a Minecraft mob of the same behavior class. Among the mobs of that class,
`units.ANIMALS` uses the mob that looks most similar. `tests/test_units.py` reads this table and checks it
against the code and against a table of Minecraft mob classes.

The owner's rule (#43):
> Passive AoE2 animals should map to passive MC animals, passive but aggressive on hit should be the same,
> and aggressive by default should also be the same.

## Classes

| Class | AoE2 | Minecraft 1.21.1 |
|---|---|---|
| passive | Flees or does nothing when hit (deer, herdables) | Never attacks a player: `sheep`, `cow`, `pig`, `chicken`, `horse`, `donkey`, `camel`, `rabbit`, `fox`, `ocelot`, `turtle` |
| defensive | Fights back when hit (wild boar, elk) | Neutral, attacks when hit: `panda` (aggressive gene), `polar_bear`, `llama`, `wolf` |
| aggressive | Attacks villagers on sight (wolves, big cats) | Hostile: `hoglin`, `silverfish`; or a neutral mob that is angry (see below) |
| military | Cheat and military units of a player | Out of the rule: the look wins |

The `goat` is not in a class: it rams players and mobs on its own, but does not fight back when hit.
So no animal uses it.

## Can NBT make a neutral mob aggressive?

Wolves and polar bears have the tags `AngerTime` (ticks) and `AngryAt` (UUID of the target).
From the Minecraft 1.21.1 code (`NeutralMob`, not tested in the game yet):
- `AngerTime > 0` makes the mob angry. An angry wolf has red eyes and a raised tail, so it looks hostile.
- The mob attacks a player only if `AngryAt` is the UUID of that player, or if the gamerule `universalAnger`
  is true. The converter does not know the UUID of the player.
- The anger time counts down only while the mob has no player target and has AI. All mobs have `NoAI` now,
  so `AngerTime = 2147483647` stays.

So the converter gives aggressive wolves, big cats and the polar bear `AngerTime = 2147483647`. They look angry.
They attack all players only with `universalAnger` (a later option, with AI, see #32). That gamerule
changes all neutral mobs of the world, so the converter does not set it now.

## Table

Sources: the AoE2 wiki pages in the table (read on 2026-10-25 through the MediaWiki API). The "Animal" page
lists the herdable animals and the huntable animals without an attack. Minecraft classes: Minecraft 1.21.1.

| AoE2 animal | AoE2 behavior | Source | Minecraft mob | Variant | Mob class in Minecraft | Reason |
|---|---|---|---|---|---|---|
| `BROWN_BEAR` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Brown_Bear) | `hoglin` | – | hostile | No hostile mob looks like this animal. The hoglin is a large, hostile animal. |
| `CROCODILE` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Crocodile) | `hoglin` | – | hostile | No hostile mob looks like this animal. The hoglin is a large, hostile animal. |
| `DEER` | passive | [wiki](https://ageofempires.fandom.com/wiki/Deer) | `horse` | Variant=770 | passive | No deer exists. A chestnut horse with white dots. |
| `DIRE_WOLF` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Dire_Wolf) | `wolf` | variant=black, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `ELEPHANT` | defensive | [wiki](https://ageofempires.fandom.com/wiki/Elephant) | `polar_bear` | – | neutral (fights back when hit) | A large, heavy, neutral animal. The ravager (old mapping of the elephant) is hostile. |
| `IBEX` | passive | [wiki](https://ageofempires.fandom.com/wiki/Ibex) | `sheep` | Color=12 | passive | The goat rams on its own: a brown sheep is the passive mob with horns-like wool. |
| `IRON_BOAR` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Iron_Boar) | `hoglin` | – | hostile | No hostile mob looks like this animal. The hoglin is a large, hostile animal. |
| `JAGUAR` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Jaguar) | `wolf` | variant=spotted, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `JAVELINA` | defensive | [wiki](https://ageofempires.fandom.com/wiki/Javelina) | `panda` | MainGene=aggressive, HiddenGene=aggressive | neutral (fights back when hit) | No neutral pig exists. A panda with the aggressive gene fights back when hit. The brown look and the aggressive gene cannot go together. |
| `KOMODO_DRAGON` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Komodo_Dragon) | `hoglin` | – | hostile | No hostile mob looks like this animal. The hoglin is a large, hostile animal. |
| `LION` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Lion) | `wolf` | variant=chestnut, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `OSTRICH` | passive | [wiki](https://ageofempires.fandom.com/wiki/Ostrich) | `chicken` | – | passive | A large bird: the chicken is the only passive bird on land. |
| `RABID_WOLF` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Rabid_Wolf) | `wolf` | variant=ashen, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `RHINOCEROS` | defensive | [wiki](https://ageofempires.fandom.com/wiki/Rhinoceros) | `panda` | MainGene=aggressive, HiddenGene=aggressive | neutral (fights back when hit) | No neutral pig exists. A panda with the aggressive gene fights back when hit. The brown look and the aggressive gene cannot go together. |
| `SNOW_LEOPARD` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Snow_Leopard) | `wolf` | variant=snowy, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `STORMY_DOG` | military | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `wolf` | variant=black, AngerTime=2147483647 | – | Cheat or military unit of a player, not wild: out of the rule. The look wins. |
| `TIGER` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Tiger) | `wolf` | variant=striped, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `WILD_BACTRIAN_CAMEL` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `camel` | – | passive | Passive camelid. The llama spits back when hit, so it is not passive. |
| `WILD_BOAR` | defensive | [wiki](https://ageofempires.fandom.com/wiki/Boar) | `panda` | MainGene=aggressive, HiddenGene=aggressive | neutral (fights back when hit) | No neutral pig exists. A panda with the aggressive gene fights back when hit. The brown look and the aggressive gene cannot go together. |
| `WILD_CAMEL` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `camel` | – | passive | Passive camelid. The llama spits back when hit, so it is not passive. |
| `WILD_HORSE_A` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `GREY_WOLF` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Wolf) | `wolf` | variant=pale, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `ZEBRA` | passive | [wiki](https://ageofempires.fandom.com/wiki/Zebra) | `horse` | Variant=1024 | passive | A white horse with black dots. |
| `ALFRED_THE_ALPACA` | military | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `llama` | Variant=1 | – | Cheat or military unit of a player, not wild: out of the rule. The look wins. |
| `BACTRIAN_CAMEL` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `camel` | – | passive | Passive camelid. The llama spits back when hit, so it is not passive. |
| `COW_A` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `cow` | – | passive |  |
| `COW_B` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `cow` | – | passive |  |
| `COW_C` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `cow` | – | passive |  |
| `COW_D` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `cow` | – | passive |  |
| `DONKEY` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `donkey` | – | passive |  |
| `FURIOUS_THE_MONKEY_BOY` | military | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `ocelot` | – | – | Cheat or military unit of a player, not wild: out of the rule. The look wins. |
| `GOAT` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `sheep` | Color=8 | passive | The goat rams on its own: a light gray sheep. |
| `GOOSE` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | passive |  |
| `HORSE_A` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `HORSE_B` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `HORSE_C` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `HORSE_D` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `HORSE_E` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `LLAMA_A` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `camel` | – | passive | Passive camelid. The llama spits back when hit, so it is not passive. |
| `WAR_PENGUIN` | military | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | – | Cheat or military unit of a player, not wild: out of the rule. The look wins. |
| `PIG` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `pig` | – | passive |  |
| `SHEEP` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `sheep` | Color=0 | passive |  |
| `TURKEY` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | passive |  |
| `WATER_BUFFALO` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `cow` | – | passive |  |
| `GAZELLE` | passive | [wiki](https://ageofempires.fandom.com/wiki/Gazelle) | `horse` | Variant=1 | passive | No antelope exists. A creamy horse. |
| `MOUFLON` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `sheep` | Color=12 | passive | wild sheep |
| `GOAT_UNCONVERTIBLE` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `sheep` | Color=8 | passive | The goat rams on its own: a light gray sheep. |
| `HUNNIC_HORSE` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `ARGALI` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `sheep` | Color=12 | passive | wild sheep |
| `CHICKEN_A` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | passive |  |
| `WILD_CHICKEN_A` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | passive |  |
| `CHICKEN_B` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | passive |  |
| `WILD_CHICKEN_B` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | passive |  |
| `CHICKEN_C` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | passive |  |
| `WILD_CHICKEN_C` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | passive |  |
| `BLACK_BEAR` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Black_Bear) | `hoglin` | – | hostile | No hostile mob looks like this animal. The hoglin is a large, hostile animal. |
| `POLAR_BEAR` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Polar_Bear) | `polar_bear` | AngerTime=2147483647 | neutral; with AngerTime it is angry | Angry polar bear (AngerTime). |
| `ARABIAN_WOLF` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Arabian_Wolf) | `wolf` | variant=striped, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `WILD_HORSE_B` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `WILD_HORSE_C` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `WILD_HORSE_D` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `WILD_HORSE_E` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `horse` | Variant=0 | passive |  |
| `MONKEY` | passive | [wiki](https://ageofempires.fandom.com/wiki/Monkey) | `ocelot` | – | passive | Passive, flees from players, small and quick. No monkey exists. |
| `PENGUIN_GAIA` | passive | [wiki](https://ageofempires.fandom.com/wiki/Penguin) | `chicken` | – | passive | The chicken is the only passive bird on land. |
| `RED_FOX` | passive | [wiki](https://ageofempires.fandom.com/wiki/Red_Fox) | `fox` | Type=red | passive |  |
| `ARCTIC_FOX` | passive | [wiki](https://ageofempires.fandom.com/wiki/Arctic_Fox) | `fox` | Type=snow | passive |  |
| `LLAMA_B` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `camel` | – | passive | Passive camelid. The llama spits back when hit, so it is not passive. |
| `ARCTIC_WOLF` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Arctic_Wolf) | `wolf` | variant=snowy, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `HARE_A` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `rabbit` | RabbitType=0 | passive |  |
| `HARE_B` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `rabbit` | RabbitType=0 | passive |  |
| `ARCTIC_HARE` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `rabbit` | RabbitType=1 | passive |  |
| `TAPIR` | defensive | [wiki](https://ageofempires.fandom.com/wiki/Tapir) | `panda` | MainGene=aggressive, HiddenGene=aggressive | neutral (fights back when hit) | No neutral pig exists. A panda with the aggressive gene fights back when hit. The brown look and the aggressive gene cannot go together. |
| `CAPYBARA` | passive | [wiki](https://ageofempires.fandom.com/wiki/Capybara) | `pig` | – | passive | A pig has the same size and color. |
| `GUANACO` | passive | [wiki](https://ageofempires.fandom.com/wiki/Guanaco) | `camel` | – | passive | Passive camelid. The llama spits back when hit, so it is not passive. |
| `SNAKE` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Snake) | `silverfish` | – | hostile | The silverfish is the only small, long, hostile animal. |
| `CAIMAN` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Caiman) | `hoglin` | – | hostile | No hostile mob looks like this animal. The hoglin is a large, hostile animal. |
| `BLACK_PANTHER` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Animal) | `wolf` | variant=black, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `RHEA` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | passive | A large bird: the chicken is the only passive bird on land. |
| `WAR_DOG` | military | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `wolf` | variant=black, AngerTime=2147483647 | – | Cheat or military unit of a player, not wild: out of the rule. The look wins. |
| `ELITE_WAR_DOG` | military | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `wolf` | variant=black, AngerTime=2147483647 | – | Cheat or military unit of a player, not wild: out of the rule. The look wins. |
| `ALPACA` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `camel` | – | passive | Passive camelid. The llama spits back when hit, so it is not passive. |
| `WILD_ALPACA` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `camel` | – | passive | Passive camelid. The llama spits back when hit, so it is not passive. |
| `WALRUS` | defensive | [wiki](https://ageofempires.fandom.com/wiki/Walrus) | `polar_bear` | – | neutral (fights back when hit) | A large, heavy, neutral animal. The ravager (old mapping of the elephant) is hostile. |
| `SEAL` | passive | [wiki](https://ageofempires.fandom.com/wiki/Seal) | `turtle` | – | passive | A slow, passive animal of the beach. No seal exists. |
| `LYNX` | aggressive | [wiki](https://ageofempires.fandom.com/wiki/Lynx) | `wolf` | variant=rusty, AngerTime=2147483647 | neutral; with AngerTime it is angry | No hostile cat or wolf exists. An angry wolf (AngerTime) has red eyes; the variant gives the fur color. |
| `ELK` | defensive | [wiki](https://ageofempires.fandom.com/wiki/Elk) | `llama` | Variant=2 | neutral (fights back when hit) | The llama spits back when hit, and has the size and the long neck of an elk. The goat rams on its own. |
| `PHEASANT` | passive | [Animal](https://ageofempires.fandom.com/wiki/Animal) | `chicken` | – | passive |  |
