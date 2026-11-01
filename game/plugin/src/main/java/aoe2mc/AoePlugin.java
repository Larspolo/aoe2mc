package aoe2mc;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.ServiceLoader;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

import org.bukkit.Bukkit;
import org.bukkit.FluidCollisionMode;
import org.bukkit.HeightMap;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.attribute.AttributeModifier;
import org.bukkit.block.Block;
import org.bukkit.block.data.BlockData;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.AbstractArrow;
import org.bukkit.entity.AbstractHorse;
import org.bukkit.entity.AbstractSkeleton;
import org.bukkit.entity.Arrow;
import org.bukkit.entity.Boat;
import org.bukkit.entity.Camel;
import org.bukkit.entity.Creeper;
import org.bukkit.entity.Display;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Hoglin;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Marker;
import org.bukkit.entity.Minecart;
import org.bukkit.entity.Mob;
import org.bukkit.entity.Pig;
import org.bukkit.entity.Pillager;
import org.bukkit.entity.Player;
import org.bukkit.entity.Projectile;
import org.bukkit.entity.TextDisplay;
import org.bukkit.entity.Villager;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.entity.EntityCombustEvent;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.EntityRegainHealthEvent;
import org.bukkit.event.entity.EntityTargetEvent;
import org.bukkit.event.entity.EntityTransformEvent;
import org.bukkit.event.entity.ProjectileHitEvent;
import org.bukkit.event.entity.SlimeSplitEvent;
import org.bukkit.event.inventory.ClickType;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.vehicle.VehicleDamageEvent;
import org.bukkit.event.vehicle.VehicleDestroyEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scoreboard.Criteria;
import org.bukkit.scoreboard.Objective;
import org.bukkit.scoreboard.Scoreboard;
import org.bukkit.scoreboard.Team;
import org.bukkit.util.Transformation;
import org.bukkit.util.Vector;
import org.joml.AxisAngle4f;
import org.joml.Vector3f;

import com.destroystokyo.paper.entity.Pathfinder;
import com.destroystokyo.paper.entity.RangedEntity;
import com.destroystokyo.paper.entity.ai.Goal;
import com.destroystokyo.paper.entity.ai.GoalKey;
import com.destroystokyo.paper.entity.ai.GoalType;

import io.papermc.paper.event.player.PlayerClientLoadedWorldEvent;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;

/**
 * Orders for the units of the game program, with Minecraft path finding (#435). Vanilla has no command for
 * "walk to this point", so this plugin gives one to RCON:
 *   aoe moveto <selector> <x> <y> <z> [speed]   walk on the path of Mob#getPathfinder
 *   aoe neutral <team>:<team>,...|- ...        the neutral stances of the players (#1645): the units and buildings of
 *                                              the first team do not attack the units of the listed teams by
 *                                              themselves (an order does). Each call replaces all stances; "-": none
 *   aoe accuracy <selector> <part> [<miss part> <blocks>]  the part of the siege shots (blast 0) and arrows of
 *                                              the unit that hit a unit target, the others miss (AoE2 accuracy: the
 *                                              Trebuchet 15 %, Huns 50 %, #2479, game/combat.py accuracy_command).
 *                                              Default 1: each shot hits. With the miss fields a missed arrow hurts
 *                                              one random other enemy unit within blocks of the target with miss part
 *                                              of the damage (the Arambai, #4549); none there: no hit
 *   aoe afterblast <selector> <ticks> <attack> <blocks> <times> [buildings]
 *                                              Thunderclap Bombs (#4369): ticks after a shot of the unit lands, a
 *                                              second blast there hits each enemy unit within blocks with times melee
 *                                              hits of attack (no own or allied unit); buildings: only a shot at a
 *                                              building or at the ground (the anti-building shot of the Lou Chuan)
 *   aoe allies <team>,<team>,...|- ...         the alliances of the players (#1315): allied teams are one side for the
 *                                              arrows of buildings, the hit back and the attack alerts. Each call
 *                                              replaces all alliances; "-": no allies
 *   aoe arrows <uuid> <n>                      the arrows of each shot of a building: its base (an empty town center
 *                                              0, #1201) and 1 for each garrisoned villager or foot archer (#1113,
 *                                              game/garrison.py); 0: it does not shoot. Default 1
 *   aoe arrows <uuid> <n> <pass> <part>        also: its arrows hurt the enemy units on their line up to pass blocks
 *                                              past its range, with this part of the damage (Svan Towers, #4282)
 *   aoe attack <selector> <target selector>    Mob#setTarget: the mob attacks with its own AI
 *   aoe NAME ...                           the command of a unit ability: each class of Ability (#4589)
 *   aoe dodge <selector> <shots> <ticks> [melee 0|1]  the unit dodges projectiles (the Shrivamsha Rider, #4399,
 *                                              game/combat.py dodge_command): a gauge of shots takes each projectile
 *                                              hit with no damage and fills by shots in ticks; melee hits pass.
 *                                              melee 1: it takes melee hits instead, projectiles pass (Iron Pagoda,
 *                                              #4465). Default 0
 *   aoe speedcharge <selector> <speed> <min> <max>  the unit walks speed (a factor, 0.25 = 25 %) faster while its
 *                                              target is min to max blocks away (the Samurai, #4545, game/combat.py
 *                                              speed_charge_command); nearer (at its hit) the normal speed again
 *   aoe pack <selector> <per> <blocks> <max> <tag>,...  the unit gets +1 attack for every per own units with one of
 *                                              the tags within blocks, up to max; it does not count itself (the
 *                                              Monaspa, #4469, game/combat.py pack_command)
 *   aoe aura <selector> <blocks> <speed> <attack> <tag>,...  the own units with one of the tags within blocks of
 *                                              the unit move speed and attack attack faster (fractions); two auras do
 *                                              not add up (the Centurion, #4470, game/abilities/aura.py, Aura.java)
 *   aoe sunder <selector> <n>                  each hit of the unit on a unit lowers its melee and pierce armor by n,
 *                                              down to 0 (the Obuch, #4466, game/combat.py sunder_command). A later
 *                                              aoe stats of the target (an upgrade) sets its armor again
 *   aoe attackground <selector> <x> <y> <z>    AoE2 "Attack Ground" (#4078): a siege unit with a blast walks into its
 *                                              range of the point and shoots there with its reload until a new order
 *   aoe ballistics <team> on|off               Ballistics of the player (#1549): its archers and buildings aim where a
 *                                              moving target will be
 *   aoe batch <command> ...                    run the commands in this order, each URL-encoded ("+" is a space): one
 *                                              RCON round trip for many commands, with no feedback in the log (#2761:
 *                                              a round trip took 2 to 5 ms at a 45 ms tick, the replay fell behind)
 *   aoe camera <players> on <y> <x0> <z0> <x1> <z1> <speed>   the camera mode (Camera.java, game/camera.py): a
 *                                              floor of barrier blocks at y that only the player sees and
 *                                              feels, the walk speed times speed, no block reach
 *   aoe camera <players> off                   the normal mode; aoe camera <player>: "Camera: on|off"
 *   aoe gate <team> <x0> <y0> <z0> <x1> <y1> <z1>
 *                                              a gate of the team (#1325, Gates.java): its iron bars in the box rise
 *                                              while an own or allied unit is near or walks a path through it; the
 *                                              units of the team plan their paths with the gate raised (#1656)
 *   aoe gate lock|unlock <x> <z>               the trigger effects "Lock Gate", "Unlock Gate" (#2762): the gates
 *                                              with the block column x z keep their bars down for all units
 *   aoe goals <selector>                       the goals of the first unit (#436), for checks
 *   aoe heatmap <tile> <n> <x,y,color,shade> ... [end]   the heat map of the record as a map item for the
 *                                              spectators at the replay end (#5457, Heatmap.java)
 *   aoe hide <players> <uuid> ...              Player#hideEntity: the players do not see these entities, also a
 *                                              player that joins later (#1302: the enemy units out of sight in the
 *                                              view of one replay player). With team=T in the selector: only a
 *                                              player of team T that joins later, and no spectator (#2921).
 *                                              The riders of an entity (a ship crew, a war elephant rider) go
 *                                              with it, also on the minimap (#3674)
 *   aoe hide <players> team                   each player sees the units of the hides of its own team (or of all
 *                                              players) as hidden and all other units of the hides (a person who
 *                                              joins a team or changes it, #3070)
 *   aoe hide <players> view <uuid> ...         the same for these players only (the view of a spectator, #2901):
 *                                              the minimap and a player that joins later do not change
 *   aoe hits                                   "Hits: <team> ...": the teams with an enemy hit on a unit or a
 *                                              building since the last call (the battle music, #5342, Alerts)
 *   aoe stance <selector> <aggressive|defensive|stand_ground|no_attack>
 *                                              the AoE2 stance of a unit (#1104): no_attack never attacks without an
 *                                              order, stand_ground attacks only an enemy in its range and does not walk,
 *                                              defensive chases an enemy only CHASE blocks past its range (#1105)
 *   aoe stance <selector>                      the stance of the first unit (#1107), for checks
 *   aoe stats <selector> <hp> <attack> <melee armor> <pierce armor> <ranged 0|1|2> <classes|-> <class:bonus,...|->
 *             [reload ticks [key=value ...]]  the AoE2 values (the optional keys in any order, #4460: taken, friendly,
 *                                              less, ignore, rage, reflect, dot=damage:ticks:classes)
 *                                              of a unit (#514, combat.stats_command); a melee
 *                                              unit hits once per reload (#848, default 20: the vanilla cooldown);
 *                                              taken: the factor of the bonus damage that it takes (#2248, default 1);
 *                                              friendly: the factor of the blast damage of own and allied units on it
 *                                              (Jurchen military units 0.5, #2418, default 1); less: class:n,... the
 *                                              damage less from an attacker of the class (Royal Heirs, "-": none);
 *                                              ignore: 1 when its hits ignore a positive armor (Wootz Steel, #4331);
 *                                              rage: the attack more for each 10 % of its lost hit points (Hamask);
 *                                              reflect: the part of a hit with no projectile on it that the attacker
 *                                              takes back (Lamellar Armor, #4332); dot: each hit on a
 *                                              unit or building of these classes ("-": each) deals this damage over
 *                                              time (Dot.java, #4339)
 *   aoe stop <selector>                        stop the walk and turn the AI off: the unit stands still (#437)
 *   aoe throw <selector> <ticks> <gap> <blocks> <shots>
 *                                              Gothikon (#4368): a melee unit also throws an axe (an arrow with the
 *                                              values of the unit) at its target within blocks; it holds at most shots
 *                                              axes, one charges in ticks, two throws are gap ticks apart
 *   aoe unwear <selector>                      forget the kept blocks of the damage stages of each building target: the
 *                                              next stage keeps the blocks of a new design (a wall technology, #3071)
 *   aoe range <selector> off                  the unit shoots no more: no range goal (melee mode of the Ratha, #4504)
 *   aoe range <selector> <blocks> <ticks> [blast [min [pass [part]]]]
 *                                              a ranged unit shoots from this range, one shot per ticks (#515); a
 *                                              shot with a blast radius in blocks hits all units near the target, and
 *                                              a siege unit (a minecart) shoots too (#1050); blast 0: a siege shot
 *                                              that hits only the target (the Scorpion, #1062); min: no shot at a
 *                                              target nearer than these blocks (the AoE2 minimum range, #1350); pass:
 *                                              the bolt flies these blocks past the range and hurts the enemy units
 *                                              on its line with half the damage (the Scorpion, #1401), or with
 *                                              this part of it; blast "-": no blast, the mob shoots and its shot
 *                                              passes through (the chakram thrower, #1638)
 *   aoe sees <player> <uuid>                   "Sees: 1" or "Sees: 0" (Player#canSee), for checks
 *   aoe show <players> <uuid> ...              Player#showEntity: the players see these entities again (#1302)
 *   aoe show <players> all                     the players see all the units that a team=T hide hides (a spectator,
 *                                              team spec, #2921); a hide with no team stays
 *   aoe sight <selector> <blocks>              an idle unit attacks an enemy in this line of sight (#775)
 *   aoe sight <selector> <blocks> only|first   ... and enemy buildings: only buildings, or buildings before units
 *                                              (#1820: the ram line and the trebuchet, the elephant and cannon galleon)
 *   aoe sightedge <players> on|off             the edge of the line of sight of the player on the ground (#3330,
 *                                              Sight.java; on by default); count <team|-> <x> <z> <r>: its sides
 *   aoe building <selector> <hp> <melee armor> <pierce armor> <x0> <y0> <z0> <x1> <y1> <z1>
 *                                              make the entity the target of a building (#517, combat.building)
 *   aoe building ... <attack> <range> <reload> <min>
 *                                              the building shoots arrows: range in blocks, reload in ticks (#1111),
 *                                              no shot at a unit nearer than min blocks (the AoE2 minimum range, #1546)
 *   aoe building ... <classes>                 its armor classes (default building,standard: a wall, a gate and the
 *                                              wonder are no standard building, #1419)
 *   aoe building ... <attack> <range> <reload> <min> <classes> <bonus>
 *                                              the arrow bonus class:n,... (Heated Shot against ships, #1548)
 *   aoe building ... <classes> <bonus> <taken>  the factor of the bonus damage that it takes (Citadels, #4281;
 *                                              bonus "-": none)
 *   aoe menu <player> <title> <slot>:<material>:<name>:<lore>[:<count>] ...
 *                                              open a chest menu (#619, game/menu.py; the texts are URL-encoded)
 *   aoe menu-add <player> <title> <slot>:<material>:<name>:<lore>[:<count>] ...
 *                                              more items of the open menu with this title (one RCON command holds
 *                                              at most 1446 bytes, #1647)
 *   aoe menu-close <player>                    close the menu of the player
 *   aoe charge <selector> <ticks> <attack> <shots> <blast> <class:bonus,...|->
 *                                              Siphons (#2165): a fire ship that hits a ship also hits each enemy unit
 *                                              within blast blocks of it with shots melee hits of attack, once per ticks
 *   aoe chargeattack <selector> <ticks> <attack> [<part> <blocks>]
 *                                              the charge of a melee hit (Comitatenses, #4370): the first melee hit
 *                                              on a unit after ticks has attack more (before the armor), then the
 *                                              charge starts again; a new unit starts full; part and blocks: the
 *                                              charged hit also hurts the near enemy units (Urumi Swordsman, #4544)
 *   aoe chargedvolley <selector> <ticks> <shots> <attack> <class:bonus,...|-> [range blocks] [ignore 0|1]
 *                                              the charged volley of a ranged unit (Xianbei Raider, #4546): a shot at
 *                                              a unit that is not siege after ticks also hits it with shots arrows of
 *                                              attack and bonus (AoE2 accuracy 100 %), then the charge starts again.
 *                                              range: a melee unit fires it at its target within range blocks before
 *                                              the melee (Fire Lancer, #4547); ignore 1: the shots ignore the armor
 *   aoe cheats <code>,<code>,...|-             the AoE2 cheat codes in the chat (#816, Cheats.java; URL-encoded)
 *   aoe deathmarks on|off                      a short mark where a replay unit dies (#846, Deaths.java)
 *   aoe deathmarks heat [T]                    the deaths per tile of T blocks and team (#5458)
 *   aoe destroy <selector>                     the buildings fall as at 0 hit points: "Destroy: <n> buildings" (#819)
 *   aoe detonate <selector> <attack> <blast> <class:bonus,...|-> [foes]
 *                                              Incendiaries (#2165): the ship explodes when it sinks; each unit within
 *                                              blast blocks takes a melee hit of attack, as in the blast of a
 *                                              demolition ship also the own units; the last word foes: not the
 *                                              own or allied units (Thunderclap Bombs, #4367)
 *   aoe elevation <blocks> <team>:<up>:<low>:<high> ...
 *                                              the AoE2 elevation rule (#2307, game/combat.py elevation): a hit from
 *                                              blocks or more higher takes up (of the attacker's team) times high (of
 *                                              the target's), from blocks or more lower low (of the target's); a team
 *                                              not named: 1.25:0.75:1. Blocks 0: no rule (the default)
 *   aoe label <selector> [name]                show the name line again (after a selection change); a name sets
 *                                              the name of a building target (#661); a minecart: its crew (#1352)
 *   aoe lore <material> <name> <text> [<key>]  the last lore line of each menu item with this material and name: the
 *                                              AoE2 help text (#1160, train.HELP; URL-encoded). Sent once at the
 *                                              setup, so the menu commands stay below the RCON limit
 *   aoe minimap on|off|pixel <x> <z>           the live units as dots in their team color on map 0, once per
 *                                              second (#1237, Minimap.java); pixel: the map pixel of a block
 *   aoe minimap building <x0> <z0> <x1> <z1> <team>|unbuild <x0> <z0>   a replay building as a square on map 0 (#1238)
 *   aoe minimap flare <x> <z> <team> <ticks> [<viewers>]   a blinking cross of a flare on map 0 for <ticks> (#2405);
 *                                              viewers "p1,p3": only these teams see it (#2676)
 *   aoe minimap fog <tile> <n>|off, see|dim <y,x0,x1> ..., tile <x> <z>
 *                                              the fog of the view player on map 0 (#1567): black unexplored tiles,
 *                                              dark explored tiles out of sight; tile: the fog of a block
 *   aoe minimap know <team> <x0,z0> ...        the buildings that the team saw before: their squares show in its
 *                                              fog (#3079, a load, a second "polo")
 *   aoe minimap frame <side>|off, square <name>   a white square of <side> blocks around each player on map 0, only
 *                                              for that player (#1762); square: its pixels and color
 *   aoe where <selector> [from]                "Where <count>: <uuid> <x> <y> <z> <order 0|1> <target 0|1>, ..." for
 *                                              WHERE_PAGE units from index `from` in UUID order (#813, tools/replay_drift.py);
 *                                              target 1 also after a target or a hit since the last answer (#1169)
 *   aoe speed <selector> <speed>               the movement_speed of each unit; a siege unit (a minecart) gets its
 *                                              carrier first (#836): an invisible small pig that walks for it
 *   aoe view <player> <x> <z>                  the player goes above the block x z and faces it (#1830, Alerts.view):
 *                                              the "Go to" menu, game/goto.py
 *   aoe volley <selector> <n> <attack>         each shot of the unit fires n more arrows at its target, each with this
 *                                              AoE2 attack and no bonus (0: the values of the unit): the Armenian
 *                                              galleys and dromons (#2379, game/train.py volley_command), the
 *                                              technologies with the key "volley" (#4338): also a siege shot
 *   aoe vsunits <selector> <attack> <bonus> <blocks>   the second attack mode of the unit (the Lou Chuan, #4505,
 *                                              game/combat.py vs_units_command): at a unit (not a building) it
 *                                              shoots from this range with this pierce attack and bonus
 *   aoe box <player> <x> <z> <dye>             draw the selection box from this corner to the look (#795, Border.java)
 *   aoe box-clear <player>                     end the border of the selection box
 *   aoe box-corner <player>                    the block X Z of the last far corner of the border (#3082, a check)
 *   aoego <x> <z>                              (no permission) the player goes to a view of an alert place of the
 *                                              own team (#1816, Alerts.go): the click of an attack alert line
 * Converted units have no AI (NoAI): an order turns it on. Such a unit finds no path before its first AI tick
 * (it is not "on the ground" yet), and vanilla goals (a random stroll) can take the navigation of a walking unit:
 * so the order sends the path again every 2 ticks (#437: 10 ticks made each walk 0.5 s longer), until the unit
 * arrives or 50 tries (5 s) found no path.
 * The path search reaches only about the follow range of the mob (16 blocks for a cow): an order raises the
 * attribute follow_range to twice the distance + 32, at most 128. Longer ways need waypoints.
 * An order also sets the attribute step_height to STEP: the ground of a map has many steps of one block,
 * and a jump on each made the replay units walk at 64 % of their speed (#829). A step with a moss carpet or snow on it
 * is higher than 1 block: at 1, a scout stood still in front of it (#851).
 * The path of a unit on a slope at an angle goes in L steps: steer() aims it on the ground at a path point up to LOOK
 * blocks ahead, and glide() does the same in the air (#1022: a horse; #851: a smaller unit, only on a slope).
 * With the AI on, a unit keeps only the goals that fit AoE2 (#436): its attack goals and "float" (it swims).
 * Wandering, looking around, panic, the choice of its own targets (a zombie attacks each villager), despawning and
 * the burning in the sun go. So a unit stands still without an order and attacks only the target of an order,
 * and an attack order skips the units of the team of the target (scoreboard teams of the datapack, #358).
 * A military unit without an order and without a target attacks back when a unit of another team hits it, as with
 * the AoE2 default stance (#733). The vanilla goal hurt_by also hits back at its own team and calls the mobs of its kind,
 * so the hit handler sets the target. A unit that walks (aoe moveto) continues; villagers, monks and kings
 * (no unit classes or no attack) and Gaia animals (no AoE2 values) do not attack back. A unit with a line of sight
 * fights also without a unit class (Furious the Monkey Boy, #1995).
 * A unit with a line of sight (aoe sight) and the same rules also attacks the nearest enemy unit in its sight, each
 * second (#775). The vanilla goal nearest_attackable_target also chooses units of the own team, players and animals,
 * and has no AoE2 sight: tame() drops it.
 * A stance (aoe stance, #1104) changes only what a unit does without an order: "no attack" does not attack back and
 * does not attack an enemy in its sight; "stand ground" does so only for an enemy in its range (a melee unit: next to
 * it), keeps its place (RangeGoal shoots without a walk) and drops the target when it goes out of the range.
 * "defensive" (#1105) attacks as "aggressive" (the default), but keeps the place where its fight started: past its range
 * + CHASE from it, when its target is past its sight + CHASE from it (#1968), or when the target is dead, it drops the
 * target and walks back there with an order (as aoe moveto).
 * An order (aoe moveto, aoe attack) works with each stance, as in AoE2, and drops the place.
 * A villager walks with its brain, not with goals: it gets NoAI when it arrives, else it strolls away (#438).
 * `aoe stop` stops a walk and sets NoAI (#437: a villager without a path).
 * A hit of a unit with AoE2 values on another one takes the AoE2 damage (#514, combat.damage): max(1, attack - armor
 * + bonus). The plugin cancels the vanilla damage and sets the health: so vanilla armor items, enchantments, effects,
 * difficulty and knockback (AoE2 has none) do not change it. Max health is the attribute max_health.
 * A ranged unit (#515) gets the goal "aoe_range" in place of the vanilla bow, crossbow and trident goals: their
 * range and interval are fixed in the goal objects, and the API cannot set them (no NMS in the plugin). It walks
 * on a Minecraft path to the target until the target is in range and in sight, stops, and shoots with the vanilla
 * shot of the mob (RangedEntity#rangedAttack: the trident of a drowned), or with an aimed arrow (shoot: a skeleton or pillager).
 * A siege unit with a blast (the Mangonel line, #1050) has no mob that shoots: its carrier gets the goal "aoe_range".
 * The shot hits at once (as at a building) each unit with AoE2 values within the blast radius of the target, also own
 * units (AoE2 friendly fire), each with the damage rule; an explosion particle shows it, and no block breaks.
 * A siege unit with blast 0 (the Scorpion, Trebuchet, Organ Gun, #1062) hits only its target at once.
 * A Scorpion bolt (pass > 0) also hurts the enemy units on its line up to Range + 2 tiles, with half the damage (#1401).
 * A mounted unit (#710) is a horse (its UUID in aoe2mc.json) with a rider: a horse has no attack goal. The rider gets
 * the values of "aoe stats", the range of "aoe range" and the target of "aoe attack", and the horse gets AI without goals:
 * a riding mob walks with the navigation of its vehicle (vanilla Mob#getNavigation), so the horse follows the rider.
 * A hit on the rider takes the hit points of the horse, and the rider dies with the horse (#732).
 * A ship (#1386) is a boat with a crew (units.py): aoe stats, aoe range and aoe attack go to the crew, also as a
 * target. A hit on the boat hurts the crew, the boat does not break, and the boat goes when its crew dies (it sinks).
 * The fire ship and the demolition ship (#1440) shoot as a siege unit (aoe range with a blast): the blaze and the
 * creeper of their crew have no vanilla shot. The creeper crew of a demolition ship dies after its one blast.
 * A horse regenerates by itself in vanilla, an AoE2 unit does not: the plugin cancels the REGEN healing of a unit
 * with AoE2 values (#850). Other reasons (a later Monk heal) stay.
 * A building is blocks, and a mob attacks only a living entity: an invisible mob without AI (a slime of the size of
 * the footprint, game/combat.py building) stands in the building and takes the attacks, so that the vanilla attack
 * goals and paths work (#517). The plugin keeps the hit points of the building (a building has more than the
 * 1024 of max_health) in the scoreboard aoe_hp, cancels all other damage to it and from it (no suffocation in the
 * walls, no slime touch), and at 0 removes it and fills the box of the building with air. At each 1/7 of its hit
 * points below full the building wears one stage more (6 stages): more worn blocks and holes at each stage, back at a
 * repair (wear, #1522, #1650). The vanilla melee goal hits only a target in sight, and the eye of the slime is in the walls: so a unit next to the slime that has it as
 * target hits it once per AoE2 reload (Mob#attack, the vanilla hit with the swing; #848). A ranged unit shoots
 * a building from its range to the nearest side of the target, without sight of the eye (#608). Its arrow sticks
 * in the walls, so the goal takes the hit points for each shot, and an arrow that hits the slime does nothing.
 * Vanilla has no clickable item menu: "aoe menu" opens an inventory with the items (#619). A click on an item is
 * cancelled (the player takes nothing) and sets the score aoe_menu of the player to slot + 1 (a shift click: -(slot + 1),
 * #620; a right click: slot + 1 + MENU_RIGHT, #3523); the menu stays open, so the player can click again. "aoe menu" on an open menu of the same title and size only changes the items.
 * The name line of a unit or building (#661, owner decision #658): the custom name of the mob holds the name and 5 hearts
 * ("Militia ❤❤❤❤❤", red: full, gray: empty, each heart 20 % of the hit points). It is visible only for a hurt unit or a
 * selected one (tag aoe2mc.selected, game/gather.py), as the bars in AoE2. Each hit and "aoe stats" update it.
 * A left click with the command stick (a carrot_on_a_stick with no item name: a control group item and the Game menu
 * item have one) on air, a block or a unit is cancelled (no broken block, no hit) and sets the score aoe_left of the
 * player to 1: game/gather.py clears the selection, as a click on empty ground in AoE2 (#1788).
 */
public final class AoePlugin extends JavaPlugin implements Listener {
    // ranged: the unit shoots; pierces: its hit takes the pierce armor (not so for a Throwing Axeman, #800);
    // reload: the ticks between two melee hits (#848); taken: the factor of the bonus damage that the unit takes (#2248);
    // friendly: the factor of the friendly fire (the blast of an own or allied unit) that the unit takes (#2418);
    // less: the damage less from an attacker of a class (Royal Heirs), ignores: its hits ignore the armor (Wootz Steel, #4331);
    // rage: the attack more for each 10 % of lost hit points (Hamask), reflect: the part of a melee hit that the attacker
    // takes back (Lamellar Armor, #4332)
    record Stats(int attack, int melee, int pierce, boolean ranged, boolean pierces, Set<String> classes,
                         Map<String, Integer> bonus, int reload, double taken, double friendly, Map<String, Integer> less,
                         boolean ignores, int rage, double reflect) {
        Stats(int attack, int melee, int pierce, boolean ranged, boolean pierces, Set<String> classes,
              Map<String, Integer> bonus, int reload) {
            this(attack, melee, pierce, ranged, pierces, classes, bonus, reload, 1.0, 1.0);
        }

        Stats(int attack, int melee, int pierce, boolean ranged, boolean pierces, Set<String> classes,
              Map<String, Integer> bonus, int reload, double taken, double friendly) {
            this(attack, melee, pierce, ranged, pierces, classes, bonus, reload, taken, friendly, Map.of(), false, 0, 0.0);
        }

        int damage(Stats t) {
            return damage(t, 0);
        }

        int damage(Stats t, int more) {                       // the same rule as game/combat.py damage(); more: Hamask
            int bonus = 0, cut = 0;
            for (String c : t.classes) {
                bonus += this.bonus.getOrDefault(c, 0);
            }
            for (String c : classes) {                        // the most of the classes of the attacker (Royal Heirs)
                cut = Math.max(cut, t.less.getOrDefault(c, 0));
            }
            int armor = pierces ? t.pierce : t.melee;
            return (int) Math.max(1, Math.max(0, attack + more - (ignores ? Math.min(0, armor) : armor))
                    + Math.floor(bonus * t.taken + 0.5) - cut);   // rounded half up, as combat.damage
        }
    }

    final Map<UUID, Stats> stats = new HashMap<>();
    private final Ghost ghost = new Ghost(this);
    // The unit abilities (#4589): one class each, named in META-INF/services/aoe2mc.Ability
    private final List<Ability> abilities = ServiceLoader.load(Ability.class, AoePlugin.class.getClassLoader()).stream()
            .map(ServiceLoader.Provider::get).toList();
    private final Dot dots = new Dot();                             // damage over time (Curare, #4339)
    private final Cheats cheats = new Cheats(this);
    private final ChatName chatName = new ChatName();               // the player color of a chat name (#3681)
    private final SpecChat specChat = new SpecChat();               // the chat of the spectators (#3554)
    private final TeamChat teamChat = new TeamChat();               // the team chat to the allies (#3553)
    private final Deaths deaths = new Deaths(this);
    private final Alerts alerts = new Alerts(this, AoePlugin::side);   // "under attack" for the team of the target (#1231)
    private final Minimap minimap = new Minimap(this, this::hiddenFor);   // no dot for a hidden unit (#1567)
    private final Gates gates = new Gates();                           // the gates of the game program (#1325)
    private final MapTable mapTable = new MapTable();              // a click on the framed map (#2586)
    private final Viewer viewer = new Viewer(this);                 // the game mode switch of a replay viewer (#910)
    private final Follow camera = new Follow();                     // the follow camera of a replay (#738, #1660)
    private final Camera cameraMode = new Camera();                 // the floor and speed of the camera mode
    private final Border border = new Border();
    private final Sight sight = new Sight(minimap);                 // the edge of the line of sight (#3330)

    // b: x0 y0 z0 x1 y1 z1 of box; range: the blocks from the footprint that its arrows reach, 0: no attack (#1111)
    private static final int MAX_FILL = 32768;                    // blocks of one /fill (the 26.3 default, #3076)
    private record Building(Stats stats, String box, int max, int[] b, double range, double min) {}

    final Map<UUID, Building> buildings = new HashMap<>();
    private static final String BUILDING = "aoe2mc.building";   // the tag of a target slime (combat.building)
    private final Map<UUID, Integer> arrows = new HashMap<>();       // the arrows of a shot of a building (#1113)
    private final Map<UUID, double[]> fortPass = new HashMap<>();    // blocks past the range, damage part (Svan Towers, #4282)
    private final Map<UUID, Wear> wear = new HashMap<>();             // the damage stage of a building and its blocks (#1522)
    // aoe hide: also for a player that joins later. The teams that do not see the unit, ALL: each player (#2921)
    private final Map<UUID, Set<String>> hidden = new HashMap<>();
    private static final String ALL = "*";
    private final Map<UUID, Component> names = new HashMap<>();      // the name in the name line (#661)
    private final Map<UUID, TextDisplay> labels = new HashMap<>();   // the name line over the roof of a building (#1811)
    static final String LABEL = "aoe2mc.label";                       // the tag of that text display
    private static final int HEARTS = 5;
    private static final int MENU_RIGHT = 1000;                        // a right click: slot + 1 + MENU_RIGHT (game/menu.py RIGHT, #3523)
    private static final int WHERE_PAGE = 40;                          // aoe where: about 3000 bytes per answer
    private final Map<UUID, Integer> lastHit = new HashMap<>();      // tick of the last melee hit of a unit
    private final Set<UUID> fought = new HashSet<>();                 // a target or a hit since the last aoe where (#1169)
    private static final double REACH = Math.sqrt(2.04) - 0.6;       // vanilla melee reach past the hit box
    // The AoE2 melee reach in blocks of a lance or a spear (the Kamayuk, aoe stats reach=, #5242). The plugin makes the
    // melee hits of the AoE2 units (siege()), so the reach is here: the vanilla attack_range of an item only changes
    // the hits of the vanilla goal, which onHit drops.
    private final Map<UUID, Double> reaches = new HashMap<>();

    private double reach(Entity unit) {
        return REACH + reaches.getOrDefault(unit.getUniqueId(), 0.0);
    }
    private static final double WALK = 43.4;      // blocks per second of movement_speed 1 on flat ground (game/ai.py)
    private static final double GROUND = 0.6 * 0.91;  // ground drag per tick (the friction of most blocks)
    private static final double LOOK = 3, OFF = 0.75;   // steer(): blocks ahead, blocks off the line (#1022)

    private static final class Order {
        final Location goal;
        final double speed;
        final int start = Bukkit.getCurrentTick();
        int fails;
        int at = -1;                                // steer(): the tick, place and velocity of the last steer (#1344)
        double px, pz, vx, vz;

        Order(Location goal, double speed) {
            this.goal = goal;
            this.speed = speed;
        }
    }

    private final Map<UUID, Order> orders = new HashMap<>();
    private final Map<UUID, Float> wet = new HashMap<>();       // the water malus of a unit before dry() blocked it
    private boolean noMalus;                                    // the warning of malus() once

    // min: no shot at a target nearer than this (blocks, the AoE2 minimum range of the Mangonel line ..., #1350)
    // pass: the blocks that a bolt flies past the range and hurts the enemy units on its line (the Scorpion, #1401),
    // part: the part of the damage on them (0.5, the chakram 1.0, #1638)
    private record Range(double blocks, int ticks, double blast, boolean siege, double min, double pass, double part) {
    }

    private final Map<UUID, Range> ranges = new HashMap<>();
    // A charge attack (Siphons) or the blast at death (Incendiaries) of a fire ship crew (#2165): shots melee hits of
    // stats on each unit within blast blocks, at most once per ticks. Vanilla has no "on death" command or second attack.
    private record Charge(int ticks, Stats stats, int shots, double blast) {
    }

    private final Map<UUID, Charge> charges = new HashMap<>();
    // the part of the siege shots at a unit that hit (aoe accuracy, #2479): the Trebuchet 0.15; missing: 1
    private final Map<UUID, Double> accuracy = new HashMap<>();
    private final Map<UUID, double[]> misses = new HashMap<>();   // aoe accuracy (#4549): {part, blocks} of a miss
    private final Map<UUID, Dodge> dodges = new HashMap<>();    // aoe dodge: the shield of a unit (#4399)
    private final Map<UUID, VsUnits> vsUnits = new HashMap<>();  // aoe vsunits: the anti-unit mode of a unit (#4505)

    // The anti-unit mode of a unit with two attack modes (the Lou Chuan, #4505): pierce attack, bonus and range in blocks.
    private record VsUnits(int attack, Map<String, Integer> bonus, double blocks) {}
    private final Map<UUID, Integer> sunders = new HashMap<>();  // aoe sunder (#4466): the armor less per hit
    private final Map<UUID, double[]> speedCharges = new HashMap<>();   // aoe speedcharge (#4545): {speed, min, max}
    private static final NamespacedKey CHARGE_SPEED = new NamespacedKey("aoe2mc", "speed_charge");

    private final Map<UUID, Pack> packs = new HashMap<>();      // aoe pack (#4469); rider and horse share it
    private record Pack(int per, double blocks, int max, Set<String> tags) {}

    // The AoE2 dodge of a unit (#4399): "gauge" shots left at tick "at"; it fills by "shots" in "ticks", up to "shots".
    private static final class Dodge {
        final int shots, ticks;
        final boolean melee;                                 // true: it takes melee hits, not projectiles (#4465)
        double gauge;
        int at;

        Dodge(int shots, int ticks, boolean melee) {
            this.shots = shots;
            this.melee = melee;
            this.ticks = Math.max(1, ticks);
            this.gauge = shots;
            this.at = Bukkit.getCurrentTick();
        }

        boolean take() {                                     // true: the projectile does no damage
            int now = Bukkit.getCurrentTick();
            gauge = Math.min(shots, gauge + (now - at) * (double) shots / ticks);
            at = now;
            if (gauge < 1) {
                return false;
            }
            gauge -= 1;
            return true;
        }
    }
    // the extra arrows of each shot of a unit (aoe volley, #2379): {arrows, attack of each, 0: the attack of the unit}
    private final Map<UUID, int[]> volleys = new HashMap<>();
    private static final String VOLLEY = "aoe2mc.volley.";      // the tag of an extra arrow, with its attack
    private final Map<UUID, Integer> charged = new HashMap<>();      // the first tick of the next charge attack
    private final Map<UUID, int[]> meleeCharges = new HashMap<>();   // aoe chargeattack (#4370): {ticks, attack}
    private final Map<UUID, Integer> meleeCharged = new HashMap<>(); // the first tick of the next charged melee hit
    private final Map<UUID, Blast> meleeBlasts = new HashMap<>();  // the blast of a charged hit (Urumi, #4544)
    private record ChargedVolley(int ticks, int shots, Stats arrow, double range) {}  // aoe chargedvolley (#4546);
    private static final double VOLLEY_MELEE = 2.0;   // blocks: nearer, a Fire Lancer fights in melee (#4547)
    private final Map<UUID, ChargedVolley> chargedVolleys = new HashMap<>();
    private final Map<UUID, Integer> volleyCharged = new HashMap<>();  // the first tick of the next charged volley
    private final Map<UUID, Charge> detonations = new HashMap<>();
    private final Set<UUID> spare = new HashSet<>();       // detonations that hurt no own or allied unit (#4367)
    // The second blast where a shot lands (aoe afterblast, #4369): charge ticks is the delay, shots the hits; buildings:
    // only a shot that is not at a unit
    private record AfterBlast(Charge charge, boolean buildings) {
    }

    private final Map<UUID, AfterBlast> afterBlasts = new HashMap<>();
    private static final String LANDED = "aoe2mc.landed";   // a projectile that made its second blast
    // A charged ranged attack of a melee unit (Gothikon, #4368, aoe throw): at most shots axes, one charges in ticks;
    // axes: {charged axes, the tick where the next charge started, the first tick of the next throw}
    private record Throw(int ticks, int gap, double blocks, int shots) {
    }

    private final Map<UUID, Throw> throwers = new HashMap<>();
    // Trample damage (Trample, #4397): part of the AoE2 damage within blocks of the target; damage > 0: a fixed damage
    record Blast(double part, double blocks, double damage, boolean ignore) {
    }

    private final Map<UUID, int[]> axes = new HashMap<>();
    private final Map<UUID, Double> sights = new HashMap<>();       // the line of sight of a unit in blocks (#775)
    private final Map<UUID, String> modes = new HashMap<>();        // "only" or "first": it takes buildings (#1820)
    private static final Set<String> STANCES = Set.of("aggressive", "defensive", "stand_ground", "no_attack");
    private final Map<UUID, String> stances = new HashMap<>();      // no entry: aggressive (#1104)
    private final Set<UUID> held = new HashSet<>();                 // stand ground units with a target of their own
    private final Map<UUID, Location> posts = new HashMap<>();      // defensive units in a fight: their place (#1105)
    private final Map<UUID, Location> grounds = new HashMap<>();    // the point of an attack ground order (#4078)
    // defensive: the blocks past its range that a unit chases. The AoE2 wiki ("Unit stance": "will follow for a certain
    // number of tiles before returning to their original position") gives no number: 3 tiles of 4 blocks (#1105).
    private static final double CHASE = 12.0;
    private static final double MELEE = 2.0;          // stand ground: the blocks to an enemy that a melee unit attacks
    static final String CARRIER = "aoe2mc.carrier";                  // the tag of the mob that carries a siege unit
    static final String NO_TARGET = "aoe2mc.notarget";               // no unit or tower chooses it as a target (#2826)
    private static final double[] CLIMB = {0.75, 0.15};               // up and forward (blocks per tick) out of water
    private static final double STEP = 1.25;                         // a step of 1 block with snow[layers=2] (#851)
    private static final double CARRIER_SCALE = 0.3;                 // a pig of 0.27 blocks: the minecart stays low
    private final GoalKey<Mob> rangeKey = GoalKey.of(Mob.class, new NamespacedKey("aoe2mc", "aoe_range"));
    private final GoalKey<Mob> chaseKey = GoalKey.of(Mob.class, new NamespacedKey("aoe2mc", "aoe_chase"));
    // the vanilla goals that walk a mob to its target (the llama spits as a melee unit): a melee unit without one gets
    // "aoe_chase" (#1968)
    private static final Set<String> MELEES = Set.of("melee_attack", "zombie_attack", "ocelot_attack", "skeleton_melee",
            "spear_use", "ranged_attack", "ranged_bow_attack", "ranged_crossbow_attack");
    // the vanilla ranged goals that "aoe_range" replaces
    private static final Set<String> SHOTS = Set.of("ranged_attack", "ranged_bow_attack", "ranged_crossbow_attack",
            "skeleton_melee");

    /** Shoot the target of the mob from the AoE2 range: walk until it is in range and in sight, then stop. */
    private final class RangeGoal implements Goal<Mob> {
        private final Mob mob;
        private final Range range;
        private int next, ticks;                  // server tick of the next shot: tick() runs only each 2nd tick

        RangeGoal(Mob mob, Range range) {
            this.mob = mob;
            this.range = range;
        }

        @Override
        public boolean shouldActivate() {
            LivingEntity t = target(mob);
            return t != null && t.isValid() && !t.isDead() || range.siege && grounds.containsKey(mob.getUniqueId());
        }

        @Override
        public void stop() {
            mob.getPathfinder().stopPathfinding();
        }

        @Override
        public void tick() {
            Location g = grounds.get(mob.getUniqueId());
            if (g != null && range.siege) {
                ground(g);
                return;
            }
            LivingEntity t = target(mob);
            // a building: the range to its nearest side, and no sight of the eye of its target in the walls (#608)
            boolean wall = buildings.containsKey(t.getUniqueId());
            double d2 = wall ? gap(mob, t) : mob.getLocation().distanceSquared(t.getLocation());
            VsUnits vs = wall ? null : vsUnits.getOrDefault(mob.getUniqueId(), vsUnits.get(crew(mob).getUniqueId()));
            double reach = vs != null ? vs.blocks() : range.blocks;     // the anti-unit mode at a unit (#4505)
            boolean near = d2 <= reach * reach && (wall || mob.hasLineOfSight(t));
            boolean close = d2 < range.min * range.min;  // inside the minimum range: it stays and does not shoot (#1350)
            if (close) {
                mob.getPathfinder().stopPathfinding();
                near = false;
            } else if (near) {
                mob.getPathfinder().stopPathfinding();
            } else if (held.contains(mob.getUniqueId())) {
                mob.getPathfinder().stopPathfinding();               // stand ground: no walk (#1104)
            } else if (!mob.getPathfinder().hasPath() || ++ticks % 10 == 0) {     // the target can move
                reach(mob, t.getLocation());
                mob.getPathfinder().moveTo(t);
            }
            mob.lookAt(t);
            int now = Bukkit.getCurrentTick();
            if (now >= next && near && range.siege) {
                next = now + range.ticks;
                blast(mob, t, range);
            } else if (now >= next && near && mob instanceof RangedEntity r) {
                int[] extra = volleys.getOrDefault(mob.getUniqueId(), new int[] {0, 0});
                if (mob instanceof AbstractSkeleton || mob instanceof Pillager) {
                    shoot(mob, t);            // the vanilla shot misses (#634), and fails for a crossbow (#633)
                    for (int k = 0; k < extra[0]; k++) {
                        shoot(mob, t).addScoreboardTag(VOLLEY + extra[1]);   // onHit gives it its attack (#2379)
                    }
                } else {
                    r.rangedAttack(t, 1.0f);
                    Stats a = stats.get(mob.getUniqueId());           // a trident has no tag: the extra hits at
                    LivingEntity v = t.getVehicle() instanceof LivingEntity h && stats.containsKey(h.getUniqueId()) ? h : t;
                    for (int k = 0; a != null && !buildings.containsKey(t.getUniqueId()) && k < extra[0]; k++) {
                        if (v.isValid() && stats.containsKey(v.getUniqueId())) {    // once (Hul'che Javelineers, #4338)
                            harm(v, stats.get(v.getUniqueId()), volley(a, extra[1]), mob);
                        }
                    }
                }
                chargedVolley(mob, t);
                next = now + range.ticks;
                Stats a = stats.get(mob.getUniqueId());
                Building b = buildings.get(t.getUniqueId());
                if (a != null && b != null) {           // the arrow sticks in the walls: the shot hits (#608)
                    hit(t, b, damage(a, b, mob, t), mob);
                    for (int k = 0; k < extra[0]; k++) {
                        hit(t, b, damage(volley(a, extra[1]), b, mob, t), mob);
                    }
                    hitEffect(t, b, mob);
                    alerts.hit(t, true, mob);
                } else if (a != null && range.pass > 0) {   // a chakram flies on through the units (#1638), not buildings
                    LivingEntity v = t.getVehicle() instanceof LivingEntity h && stats.containsKey(h.getUniqueId()) ? h : t;
                    if (v.isValid() && stats.containsKey(v.getUniqueId())) {   // AoE2 accuracy 100 % (wiki): the target
                        harm(v, stats.get(v.getUniqueId()), a, mob);        // takes the hit, the trident only shows it
                    }                                                      // and can miss (#1713, onHit)
                    pass(mob, v, range.blocks + range.pass, a, mob, range.part);
                }
            }
        }

        // Attack Ground (#4078): as a shot at a unit, but the target is a fixed point and the blast falls there.
        private void ground(Location g) {
            double d2 = mob.getLocation().distanceSquared(g);
            boolean near = d2 <= range.blocks * range.blocks && d2 >= range.min * range.min;
            if (near || d2 < range.min * range.min || held.contains(mob.getUniqueId())) {
                mob.getPathfinder().stopPathfinding();
            } else if (!mob.getPathfinder().hasPath() || ++ticks % 10 == 0) {
                reach(mob, g);
                mob.getPathfinder().moveTo(g);
            }
            mob.lookAt(g);
            int now = Bukkit.getCurrentTick();
            Entity from = crew(mob);
            if (now >= next && near && stats.get(from.getUniqueId()) instanceof Stats a) {
                next = now + range.ticks;
                blastAt(from, a, g, range.blast);
                afterBlast(from, g, false);
            }
        }

        @Override
        public GoalKey<Mob> getKey() {
            return rangeKey;
        }

        @Override
        public EnumSet<GoalType> getTypes() {
            return EnumSet.of(GoalType.MOVE, GoalType.LOOK);
        }
    }

    /** Walk a melee unit to its target when the mob kind has no vanilla melee goal (the chicken of the War Penguin,
     *  #1968): Minecraft has no attack goal for it. siege() makes the hit next to the target. */
    private final class ChaseGoal implements Goal<Mob> {
        private final Mob mob;
        private int ticks;

        ChaseGoal(Mob mob) {
            this.mob = mob;
        }

        @Override
        public boolean shouldActivate() {
            LivingEntity t = target(mob);
            return t != null && t.isValid() && !t.isDead();
        }

        @Override
        public void stop() {
            mob.getPathfinder().stopPathfinding();
        }

        @Override
        public void tick() {
            LivingEntity t = target(mob);
            if (held.contains(mob.getUniqueId())                    // stand ground: no walk (#1104)
                    || mob.getBoundingBox().expand(reach(mob), 0, reach(mob)).overlaps(t.getBoundingBox())) {
                mob.getPathfinder().stopPathfinding();
            } else if (!mob.getPathfinder().hasPath() || ++ticks % 10 == 0) {     // the target can move
                reach(mob, t.getLocation());
                mob.getPathfinder().moveTo(t);
            }
            mob.lookAt(t);
        }

        @Override
        public GoalKey<Mob> getKey() {
            return chaseKey;
        }

        @Override
        public EnumSet<GoalType> getTypes() {
            return EnumSet.of(GoalType.MOVE, GoalType.LOOK);
        }
    }

    // The entity with the AoE2 values of a shooter: the crew of a siege unit for its carrier (aoe stats, #836).
    static Entity crew(Mob mob) {
        return mob.getPassengers().isEmpty() || !(mob.getPassengers().get(0) instanceof Minecart cart)
                || cart.getPassengers().isEmpty() ? mob : cart.getPassengers().get(0);
    }

    // A blast shot (#1050): each unit with AoE2 values within r blocks of the target takes the AoE2 damage of the
    // shooter, also its own units. A mounted unit has the hit points of its horse (#732): only the horse counts.
    // r 0: a siege shot that hits only the target (#1062), and with a pass the enemy units on its line (#1401).
    private void blast(Mob mob, LivingEntity t, Range range) {
        Entity from = crew(mob);
        Stats a = stats.get(from.getUniqueId());
        if (a == null) {
            return;
        }
        int[] extra = volleys.getOrDefault(from.getUniqueId(), new int[] {0, 0});
        Location at = t.getLocation();
        for (int k = 0; k <= extra[0] && t.isValid(); k++) {   // the extra shots of a volley (aoe volley, #4338)
            blast(mob, t, range, from, k == 0 ? a : volley(a, extra[1]));
        }
        afterBlast(from, at, !buildings.containsKey(t.getUniqueId()));
    }

    // One blast shot of the crew from (the entity with the AoE2 values a) of mob at t.
    private void blast(Mob mob, LivingEntity t, Range range, Entity from, Stats a) {
        double r = range.blast;
        Building b = buildings.get(t.getUniqueId());
        Location at = t.getLocation();
        if (b != null) {                                  // a building takes the shot alone
            hit(t, b, damage(a, b, from, t), from);
            hitEffect(t, b, mob);
            alerts.hit(t, true, mob);
        } else if (r <= 0) {
            LivingEntity v = t.getVehicle() instanceof LivingEntity h && stats.containsKey(h.getUniqueId()) ? h : t;
            boolean hits = ThreadLocalRandom.current().nextDouble() < accuracy.getOrDefault(from.getUniqueId(), 1.0);
            if (v.isValid() && stats.containsKey(v.getUniqueId()) && hits) {   // AoE2 accuracy (#2479): or a miss
                harm(v, stats.get(v.getUniqueId()), a, from);
                charge(from, v);
            }
            if (range.pass > 0) {
                pass(mob, v, range.blocks + range.pass, a, from, range.part);
            }
            t.getWorld().spawnParticle(Particle.CRIT, at.clone().add(0, 1, 0), 8);
            t.getWorld().playSound(at, Sound.ENTITY_ARROW_HIT, 1.0f, 1.0f);
            return;
        }
        blastAt(from, a, at, b != null ? 0 : r);
    }

    // The blast of a shot at the point at (#1050): each unit with AoE2 values within r blocks takes the AoE2 damage of
    // the shooter, also its own units (r 0: none). A shot at a unit and an attack ground (#4078) share it.
    private void blastAt(Entity from, Stats a, Location at, double r) {
        for (Entity e : r > 0 ? at.getWorld().getNearbyEntities(at, r, r, r) : List.<Entity>of()) {
            if (e instanceof LivingEntity le && le.isValid() && stats.containsKey(le.getUniqueId())
                    && !buildings.containsKey(le.getUniqueId()) && le != from
                    && !(le.getVehicle() instanceof LivingEntity v && stats.containsKey(v.getUniqueId()))
                    && le.getLocation().distanceSquared(at) <= r * r) {
                Stats t2 = stats.get(le.getUniqueId());
                harm(le, t2, a, from, friendlyFire(from, le) ? t2.friendly : 1.0);   // friendly fire (#2418)
            }
        }
        at.getWorld().spawnParticle(Particle.EXPLOSION, at.clone().add(0, 0.5, 0), 1);
        at.getWorld().playSound(at, Sound.ENTITY_GENERIC_EXPLODE, 1.0f, 1.0f);
        if (from instanceof Creeper c) {      // the demolition ship (#1440), the petard (#2192): one blast, then it dies. No
            c.setHealth(0);                   // vanilla explosion: it breaks no block, and the damage is the AoE2 one
        }
    }

    // Gothikon (#4368, AoE2 DE wiki): a unit of aoe throw throws a charged axe at its enemy target in range, with its
    // own melee values (onHit: the arrow of a melee unit). A full unit does not charge, so the first throw of a fight
    // comes at once and the next one ticks after it. Not at a building: an arrow does not hurt it (onHit).
    private void throwAxes() {
        int now = Bukkit.getCurrentTick();
        for (Map.Entry<UUID, Throw> en : throwers.entrySet()) {
            Throw w = en.getValue();
            int[] a = axes.computeIfAbsent(en.getKey(), k -> new int[] {w.shots, now, now});
            while (a[0] < w.shots && now >= a[1] + w.ticks) {
                a[0]++;
                a[1] += w.ticks;
            }
            if (a[0] >= w.shots) {
                a[1] = now;
            }
            if (a[0] == 0 || now < a[2] || !(Bukkit.getEntity(en.getKey()) instanceof Mob mob) || !mob.isValid()) {
                continue;
            }
            LivingEntity t = target(mob);
            if (t != null && t.isValid() && !t.isDead() && !buildings.containsKey(t.getUniqueId()) && !sameTeam(mob, t)
                    && mob.getLocation().distanceSquared(t.getLocation()) <= w.blocks * w.blocks && mob.hasLineOfSight(t)) {
                shoot(mob, t);
                a[0]--;
                a[2] = now + w.gap;
            }
        }
    }

    // Siphons (#2165, wiki "Siphons"): the hit of a fire ship on a ship sets off its charge attack when it is ready.
    private void charge(Entity from, LivingEntity t) {
        Charge c = charges.get(from.getUniqueId());
        Stats s = stats.get(t.getUniqueId());
        int now = Bukkit.getCurrentTick();
        if (c == null || s == null || !s.classes().contains("ship") || now < charged.getOrDefault(from.getUniqueId(), 0)) {
            return;
        }
        charged.put(from.getUniqueId(), now + c.ticks);
        burst(from, t.getLocation(), c, true);
    }

    // The charged volley of a shot of from at t (#4546, the Xianbei Raider): with a full charge the shots extra arrows
    // hit a unit that is not siege (AoE2 accuracy 100 %, wiki "Xianbei Raider"), then the charge starts again from 0.
    private void chargedVolley(Entity from, LivingEntity t) {
        ChargedVolley c = chargedVolleys.get(from.getUniqueId());
        LivingEntity v = t.getVehicle() instanceof LivingEntity h && stats.containsKey(h.getUniqueId()) ? h : t;
        Stats s = stats.get(v.getUniqueId());
        int now = Bukkit.getCurrentTick();
        if (c == null || s == null || buildings.containsKey(v.getUniqueId()) || s.classes().contains("siege")
                || now < volleyCharged.getOrDefault(from.getUniqueId(), 0)) {
            return;
        }
        volleyCharged.put(from.getUniqueId(), now + c.ticks());
        for (int k = 0; k < c.shots() && v.isValid(); k++) {
            harm(v, s, c.arrow(), from);
        }
        v.getWorld().spawnParticle(Particle.CRIT, v.getLocation().add(0, 1, 0), 4 * c.shots());
    }

    // The charged volley of a melee unit (#4547, the Fire Lancer): it fires at its target within the range before the
    // melee ("except when in melee combat", wiki "Fire Lancer"). Vanilla melee AI has no ranged shot.
    private void meleeVolleys() {
        for (Map.Entry<UUID, ChargedVolley> en : chargedVolleys.entrySet()) {
            double r = en.getValue().range();
            if (r <= 0 || !(Bukkit.getEntity(en.getKey()) instanceof Mob mob) || !mob.isValid()) {
                continue;
            }
            LivingEntity t = target(mob);
            if (t != null && t.isValid() && !t.isDead() && t.getWorld() == mob.getWorld() && !sameTeam(mob, t)) {
                double d = mob.getLocation().distance(t.getLocation());
                if (d > VOLLEY_MELEE && d <= r && mob.hasLineOfSight(t)) {
                    chargedVolley(mob, t);
                }
            }
        }
    }

    // The values of a melee hit of from (#4370): with a full charge (aoe chargeattack) the attack is more, and the
    // charge starts again from 0, as the AoE2 charge attack (wiki "Charge attack"). The armor counts once.
    private Stats charged(Entity from, Stats a) {
        int[] c = meleeCharges.get(from.getUniqueId());
        int now = Bukkit.getCurrentTick();
        if (c == null || now < meleeCharged.getOrDefault(from.getUniqueId(), 0)) {
            return a;
        }
        meleeCharged.put(from.getUniqueId(), now + c[0]);
        return new Stats(a.attack() + c[1], a.melee(), a.pierce(), a.ranged(), a.pierces(), a.classes(), a.bonus(),
                a.reload(), a.taken(), a.friendly(), a.less(), a.ignores(), a.rage(), a.reflect());
    }


    // Thunderclap Bombs (#4369, AoE2 DE wiki): a shot of from landed at the point at (unit: at a unit). A Paper timer
    // per shot sets off the second blast there after the delay, also when from dies before. Vanilla has no such shot.
    private void afterBlast(Entity from, Location at, boolean unit) {
        AfterBlast b = afterBlasts.get(from.getUniqueId());
        if (b != null && !(b.buildings() && unit)) {
            Location p = at.clone();
            Bukkit.getScheduler().runTaskLater(this, () -> burst(from, p, b.charge(), true), b.charge().ticks());
        }
    }

    // An arrow or a trident of a unit of aoe afterblast lands on an entity or a block (#4369): one second blast per
    // shot, so not for the extra arrows of a volley, and once for a projectile that bounces off.
    @EventHandler
    public void onLand(ProjectileHitEvent ev) {
        Projectile p = ev.getEntity();
        if (p.getShooter() instanceof Entity from && afterBlasts.containsKey(from.getUniqueId())
                && p.getScoreboardTags().stream().noneMatch(t -> t.startsWith(VOLLEY)) && p.addScoreboardTag(LANDED)) {
            Entity hit = ev.getHitEntity();
            afterBlast(from, hit != null ? hit.getLocation() : p.getLocation(),
                    hit != null && !buildings.containsKey(hit.getUniqueId()));
        }
    }

    // The hits of a charge or a detonation on each unit with AoE2 values within its blast; foes: not the own or
    // allied units. A mounted unit has the hit points of its horse (#732): only the horse counts.
    private void burst(Entity from, Location at, Charge c, boolean foes) {
        double r = c.blast;
        for (Entity e : at.getWorld().getNearbyEntities(at, r, r, r)) {
            if (e instanceof LivingEntity le && le.isValid() && stats.containsKey(le.getUniqueId())
                    && !buildings.containsKey(le.getUniqueId()) && le != from
                    && !(le.getVehicle() instanceof LivingEntity v && stats.containsKey(v.getUniqueId()))
                    && !(foes && sameTeam(from, le)) && le.getLocation().distanceSquared(at) <= r * r) {
                Stats t2 = stats.get(le.getUniqueId());           // all shots; less as friendly fire (#2418)
                harm(le, t2, c.stats, from, c.shots * (friendlyFire(from, le) ? t2.friendly : 1.0));
            }
        }
        at.getWorld().spawnParticle(Particle.FLAME, at.clone().add(0, 0.5, 0), 20, r / 2, 0.3, r / 2, 0.02);
        at.getWorld().playSound(at, Sound.ENTITY_GENERIC_EXPLODE, 1.0f, 1.2f);
    }

    // AoE2 pass-through damage (#1401, wiki "Pass-through damage"): the bolt flies Range + 2 tiles in a straight line
    // and hurts each enemy unit on it with this part of the damage (half, the chakram all, #1638); the target took the
    // full hit. Not own or allied units.
    // The line is in the ground plane (x, z) with the AoE2 bolt width of 0.2 tiles (BOLT). A piercing vanilla arrow
    // (PierceLevel) is no help: the siege shot hits at once (#1062), and an arrow falls short and hits own units too.
    private static final double BOLT = 0.4;           // blocks from the line to the box of a unit: 0.1 tile × 4 blocks

    private void pass(Mob mob, LivingEntity target, double length, Stats a, Entity from, double part) {
        Entity unit = mob.getPassengers().isEmpty() ? mob : mob.getPassengers().get(0);    // the minecart has the team
        Location o = mob.getLocation();
        Vector dir = target.getLocation().toVector().subtract(o.toVector()).setY(0);
        if (dir.lengthSquared() < 1e-6) {
            return;
        }
        dir.normalize();
        Location mid = o.clone().add(dir.clone().multiply(length / 2));
        for (Entity e : o.getWorld().getNearbyEntities(mid, length / 2 + 1, 4, length / 2 + 1)) {
            if (!(e instanceof LivingEntity le) || le == target || !le.isValid() || !stats.containsKey(le.getUniqueId())
                    || buildings.containsKey(le.getUniqueId()) || le == from || le == mob
                    || le.getVehicle() instanceof LivingEntity h && stats.containsKey(h.getUniqueId())   // the horse counts
                    || sameTeam(unit, le) || sameTeam(from, le)) {
                continue;
            }
            Vector p = le.getLocation().toVector().subtract(o.toVector()).setY(0);
            double along = p.dot(dir), across = p.clone().subtract(dir.clone().multiply(along)).length();
            if (along > 0 && along <= length && across <= le.getWidth() / 2 + BOLT) {
                harm(le, stats.get(le.getUniqueId()), a, from, part);
            }
        }
    }

    // The squared distance from the feet of the mob to the nearest point of the box of the target.
    private static double gap(Mob mob, Entity t) {
        var b = t.getBoundingBox();
        var p = mob.getLocation();
        double dx = Math.max(0, Math.max(b.getMinX() - p.getX(), p.getX() - b.getMaxX()));
        double dy = Math.max(0, Math.max(b.getMinY() - p.getY(), p.getY() - b.getMaxY()));
        double dz = Math.max(0, Math.max(b.getMinZ() - p.getZ(), p.getZ() - b.getMaxZ()));
        return dx * dx + dy * dy + dz * dz;
    }

    // A vanilla arrow. The vanilla bow shot has a spread of 14 - 4 × difficulty and a slow arrow: at 20 blocks most
    // arrows miss (#634). An AoE2 archer hits a standing target almost always: aim at the middle of the target, with
    // a fast arrow that rises by the fall of its flight time. The damage handler (onHit) gives the AoE2 damage.
    private static final double ARROW_SPEED = 3.0, ARROW_GRAVITY = 0.05;     // blocks per tick, blocks per tick²

    // the sides with Ballistics (aoe ballistics, #1549); the ground friction of a walking mob (0.6 × 0.91): its velocity
    // after a tick is its step × this factor (measured on Paper: Motion 0.0636, step 0.116 blocks per tick)
    private static final Set<String> BALLISTICS = new HashSet<>();
    private static final double GROUND_DRAG = 0.546;

    // The aim from `from` at the middle of t, raised by the fall of the flight time. With Ballistics the shooter aims
    // at the place where t will be when the arrow arrives: its position plus its step × the flight time (AoE2 DE wiki).
    // A shooter with the tag aoe2mc.lead, or the crew of a ship with it, aims so without the technology (Spanish Cannon
    // Galleons, game/train.py, #2430).
    private static Vector lead(Entity shooter, Location from, LivingEntity t) {
        Vector mid = t.getLocation().toVector().add(new Vector(0, t.getHeight() * 0.5, 0));
        Vector to = mid.clone().subtract(from.toVector());
        double ticks = to.length() / ARROW_SPEED;
        if (BALLISTICS.contains(side(shooter)) || shooter.getScoreboardTags().contains("aoe2mc.lead")
                || shooter.getVehicle() != null && shooter.getVehicle().getScoreboardTags().contains("aoe2mc.lead")) {
            Vector v = t.getVelocity().setY(0).multiply(t.isOnGround() ? 1 / GROUND_DRAG : 1);
            to = mid.add(v.multiply(ticks)).subtract(from.toVector());
            ticks = to.length() / ARROW_SPEED;
        }
        return to.setY(to.getY() + 0.5 * ARROW_GRAVITY * ticks * ticks);
    }

    private static Arrow shoot(Mob mob, LivingEntity t) {
        Vector to = lead(mob, mob.getEyeLocation(), t);
        Arrow a = mob.launchProjectile(Arrow.class, to.normalize().multiply(ARROW_SPEED));
        a.setPickupStatus(AbstractArrow.PickupStatus.DISALLOWED);
        boolean bow = mob.getEquipment().getItemInMainHand().getType() == Material.BOW;
        mob.getWorld().playSound(mob, bow ? Sound.ENTITY_SKELETON_SHOOT : Sound.ITEM_CROSSBOW_SHOOT, 1.0f, 1.0f);
        return a;
    }

    // The values of an extra arrow of a volley (aoe volley, #2379): attack 0 keeps the values of the unit, else that
    // attack with no bonus (AoE2 DE: the extra projectile of an Armenian galley deals 1 attack).
    private static Stats volley(Stats a, int attack) {
        return attack <= 0 ? a : new Stats(attack, a.melee(), a.pierce(), a.ranged(), a.pierces(), a.classes(), Map.of(),
                a.reload(), a.taken(), a.friendly(), a.less(), a.ignores(), a.rage(), a.reflect());
    }

    // The values of the projectile p of a unit with the values a: those of its tag (an extra arrow), else a.
    static Stats volley(Projectile p, Stats a) {
        for (String tag : p.getScoreboardTags()) {
            if (tag.startsWith(VOLLEY)) {
                return volley(a, Integer.parseInt(tag.substring(VOLLEY.length())));
            }
        }
        return a;
    }

    // Each 2 ticks: a building with an attack (aoe building with attack, range and reload: a town center, a castle,
    // #1111) shoots one arrow per reload at the nearest unit of another team in its range. As in AoE2, the range counts
    // from the edge of its footprint. Each garrisoned villager or foot archer adds an arrow (aoe arrows, #1113): all
    // arrows of a shot go to the same target, as in AoE2. Not at a rider (its horse is the target), a garrisoned unit or a building;
    // the crew of a ship or a siege unit is a target (#3015).
    private void towers() {
        for (var en : buildings.entrySet()) {
            Building f = en.getValue();
            if (f.range <= 0 || arrows.getOrDefault(en.getKey(), 1) <= 0 || !(Bukkit.getEntity(en.getKey()) instanceof LivingEntity fort) || !fort.isValid()
                    || !ready(fort, f.stats)) {
                continue;
            }
            int[] b = f.b;
            double half = Math.max(b[3] - b[0], b[5] - b[2]) / 2.0 + 1;
            Location c = new Location(fort.getWorld(), (b[0] + b[3] + 1) / 2.0, b[1], (b[2] + b[5] + 1) / 2.0);
            LivingEntity best = null;
            double bestD = f.range * f.range;
            for (Entity o : fort.getWorld().getNearbyEntities(c, f.range + half, f.range + 16, f.range + half)) {
                if (o instanceof LivingEntity le && le.isValid() && stats.containsKey(le.getUniqueId())
                        && !buildings.containsKey(le.getUniqueId()) && !le.isInvulnerable()
                        && !(le.getVehicle() instanceof LivingEntity v && stats.containsKey(v.getUniqueId()))   // the crew of a ship counts (#3015)
                        && !calm(fort, le)) {
                    var p = le.getLocation();
                    double dx = Math.max(0, Math.max(b[0] - p.getX(), p.getX() - b[3] - 1));
                    double dz = Math.max(0, Math.max(b[2] - p.getZ(), p.getZ() - b[5] - 1));
                    if (dx * dx + dz * dz <= bestD && dx * dx + dz * dz >= f.min * f.min   // minimum range (#1546)
                            && start(fort, b, le, 0) != null) {   // no shot: the next (#1328, #3562)
                        best = le;
                        bestD = dx * dx + dz * dz;
                    }
                }
            }
            if (best != null) {
                lastHit.put(fort.getUniqueId(), Bukkit.getCurrentTick());
                for (int k = 0, n = arrows.getOrDefault(fort.getUniqueId(), 1); k < n; k++) {
                    volley(fort, b, best, k);
                }
            }
        }
    }

    // An arrow from above the edge of the footprint next to the target, aimed as the arrow of an archer (shoot): from
    // the center the arrow hits the own roof (#1202). Arrow k starts on a ring around that point, so that the arrows of
    // one shot do not fly as one; the start is above the highest block of the 3 x 3 columns around the point. A steep
    // shot (a tall tower, a near target) starts higher: the straight line to the target leaves the 3 x 3 columns above
    // their highest block, else the arrow hits the own roof (#1219).
    private static void volley(LivingEntity fort, int[] b, LivingEntity t, int k) {
        Location from = start(fort, b, t, k);
        if (from != null) {
            aim(fort, from, t);
        }
    }

    // The start of arrow k of a shot of the building with the blocks b at t (volley), or null: no free line to t.
    // AoE2 arrows fly over the buildings between (#3562): a Minecraft arrow stops in the first block on its way, and
    // its arc is too flat to clear the wall of a house next to the target. With a block on the line the arrow starts
    // above the target and falls on it, as at the end of the AoE2 arc.
    private static Location start(LivingEntity fort, int[] b, LivingEntity t, int k) {
        var p = t.getLocation();
        if (under(b, p)) {
            return side(t, k);                                       // under the building: the roof is above it
        }
        Location from = new Location(fort.getWorld(), Math.max(b[0] + 0.5, Math.min(b[3] + 0.5, p.getX())), 0,
                Math.max(b[2] + 0.5, Math.min(b[5] + 0.5, p.getZ())));
        int top = b[1];
        for (int dx = -1; dx <= 1; dx++) {
            for (int dz = -1; dz <= 1; dz++) {
                top = Math.max(top, fort.getWorld().getHighestBlockYAt(from.getBlockX() + dx, from.getBlockZ() + dz,
                        HeightMap.MOTION_BLOCKING));
            }
        }
        double ring = k == 0 ? 0 : 0.6;
        from.add(ring * Math.cos(k * 2.4), 0, ring * Math.sin(k * 2.4));
        double ty = p.getY() + t.getHeight() * 0.5, h = Math.hypot(p.getX() - from.getX(), p.getZ() - from.getZ());
        double y = top + 1.5;
        if (h > 3) {                                                   // the line at 1.5 blocks: at least top + 1
            y = Math.max(y, (top + 1 - ty * 1.5 / h) / (1 - 1.5 / h));
        }
        from.setY(y + 0.2 * (k % 3));
        if (free(from, t)) {
            return from;
        }
        Location over = p.clone().add(ring * 0.5 * Math.cos(k * 2.4), t.getHeight() + OVER + 0.2 * (k % 3),
                ring * 0.5 * Math.sin(k * 2.4));
        return free(over, t) ? over : null;
    }

    private static final double OVER = 3;          // blocks above the head: the start of an arrow over a building

    // No block between from and the middle of t: the arrow from there hits t (its arc is above that line).
    private static boolean free(Location from, LivingEntity t) {
        Vector to = t.getLocation().add(0, t.getHeight() * 0.5, 0).toVector().subtract(from.toVector());
        return from.getBlock().isPassable() && (to.lengthSquared() < 1e-6
                || t.getWorld().rayTraceBlocks(from, to, to.length(), FluidCollisionMode.NEVER, true) == null);
    }

    private static boolean under(int[] b, Location p) {
        return p.getX() >= b[0] && p.getX() < b[3] + 1 && p.getZ() >= b[2] && p.getZ() < b[5] + 1;
    }

    // A target under its building (the passage of a town center, #865): the arrow starts next to it at head height,
    // on a free side with no block on the way, else towers() takes the next enemy (#1285, #1328). Arrow k tries the
    // sides from side k.
    private static Location side(LivingEntity t, int k) {
        Location eye = t.getLocation().add(0, t.getHeight() * 0.8, 0);
        for (int i = 0; i < 4; i++) {
            int d = (i + k) % 4;
            Vector v = new Vector(d == 0 ? 1.5 : d == 1 ? -1.5 : 0, 0, d == 2 ? 1.5 : d == 3 ? -1.5 : 0);
            Location from = eye.clone().add(v);
            if (from.getBlock().isPassable() && t.getWorld().rayTraceBlocks(from, v.clone().multiply(-1), 1.5,
                    FluidCollisionMode.NEVER, true) == null) {
                return from;
            }
        }
        return null;
    }

    private static void aim(LivingEntity fort, Location from, LivingEntity t) {
        Arrow a = fort.getWorld().spawnArrow(from, lead(fort, from, t), (float) ARROW_SPEED, 0f);
        a.setShooter(fort);
        a.setPickupStatus(AbstractArrow.PickupStatus.DISALLOWED);
        fort.getWorld().playSound(from, Sound.ENTITY_ARROW_SHOOT, 1.0f, 1.0f);
    }

    /** The holder of a chest menu: it tells a menu from the other inventories. */
    private static final class Menu implements InventoryHolder {
        final String title;
        Inventory inventory;

        Menu(String title) {
            this.title = title;
        }

        @Override
        public Inventory getInventory() {
            return inventory;
        }
    }

    private static final Map<String, String> HELP = new HashMap<>();   // "material:name" -> help line (aoe lore)
    private static final Map<String, String> KEYS = new HashMap<>();   // "material:name" -> translate key (aoe lore, #5346)
    // the sender of aoe batch: the rights of the console, and its feedback goes nowhere (the console logs each line)
    private CommandSender quiet;

    private static String text(String s) {
        return URLDecoder.decode(s, StandardCharsets.UTF_8);
    }

    /** The item of "slot:material:name:lore[:count]" (lore lines split by a new line; count 1 to 99, #706), or null
     *  for a bad slot, material or count. */
    static Map.Entry<Integer, ItemStack> item(String spec) {
        String[] p = spec.split(":", -1);
        Material m = p.length >= 3 ? Material.matchMaterial(p[1]) : null;
        int slot, count;
        try {
            slot = Integer.parseInt(p[0]);
            count = p.length > 4 && !p[4].isEmpty() ? Integer.parseInt(p[4]) : 1;
        } catch (NumberFormatException e) {
            return null;
        }
        if (m == null || !m.isItem() || m.isAir() || slot < 0 || slot >= 54 || count < 1 || count > 99) {
            return null;
        }
        ItemStack it = new ItemStack(m, count);
        it.editMeta(meta -> {
            String key = KEYS.get(p[1] + ":" + text(p[2]));             // a translate key with the name as fallback (#5346)
            meta.displayName(key == null ? Component.text(text(p[2]))
                    : Component.translatable().key(key).fallback(text(p[2])).build());
            var lines = new ArrayList<Component>();
            if (p.length > 3 && !p[3].isEmpty()) {
                text(p[3]).lines().forEach(l -> lines.add(Component.text(l)));
            }
            String help = HELP.get(p[1] + ":" + text(p[2]));
            if (help != null) {
                lines.add(Component.text(help, NamedTextColor.GRAY));
            }
            if (!lines.isEmpty()) {
                meta.lore(lines);
            }
        });
        return Map.entry(slot, it);
    }

    private static Objective menuScore() {
        Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
        Objective o = sb.getObjective("aoe_menu");
        return o != null ? o : sb.registerNewObjective("aoe_menu", Criteria.DUMMY, Component.text("Menu"));
    }

    private static boolean commandStick(ItemStack it) {
        return it != null && it.getType() == Material.CARROT_ON_A_STICK && !(it.hasItemMeta() && it.getItemMeta().hasItemName());
    }

    private static void leftClick(Player p) {
        Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
        Objective o = sb.getObjective("aoe_left");
        (o != null ? o : sb.registerNewObjective("aoe_left", Criteria.DUMMY, Component.text("Left click")))
                .getScore(p.getName()).setScore(1);
    }

    private static Menu menuOf(Player p) {
        return p.getOpenInventory().getTopInventory().getHolder(false) instanceof Menu m ? m : null;
    }

    private static List<Player> players(CommandSender sender, String selector) {
        var out = new ArrayList<Player>();
        for (Entity e : select(sender, selector)) {
            if (e instanceof Player p) {
                out.add(p);
            }
        }
        return out;
    }

    private static boolean menu(CommandSender sender, String[] args) {
        var items = new ArrayList<Map.Entry<Integer, ItemStack>>();
        int size = 9;
        for (int i = 3; i < args.length; i++) {
            var it = item(args[i]);
            if (it == null) {
                sender.sendMessage("Bad item: " + args[i]);
                return true;
            }
            items.add(it);
            size = Math.max(size, (it.getKey() / 9 + 1) * 9);             // rows of 9, at most 6
        }
        String title = text(args[2]);
        int n = 0;
        for (Player p : players(sender, args[1])) {
            Menu open = menuOf(p);
            Inventory inv;
            if (open != null && open.title.equals(title) && open.inventory.getSize() == size) {
                inv = open.inventory;                                     // refresh: no close and open again
                inv.clear();
            } else {
                Menu m = new Menu(title);
                inv = m.inventory = Bukkit.createInventory(m, size, Component.text(title));
            }
            for (var it : items) {
                inv.setItem(it.getKey(), it.getValue());
            }
            if (inv != (open != null ? open.inventory : null)) {
                p.openInventory(inv);
            }
            n++;
        }
        sender.sendMessage("Menu: " + n + " players");
        return true;
    }

    /** aoe menu-add: put more items into the open menu of the title (the rest of a long menu, game/menu.py). */
    private static boolean menuAdd(CommandSender sender, String[] args) {
        var items = new ArrayList<Map.Entry<Integer, ItemStack>>();
        for (int i = 3; i < args.length; i++) {
            var it = item(args[i]);
            if (it == null) {
                sender.sendMessage("Bad item: " + args[i]);
                return true;
            }
            items.add(it);
        }
        String title = text(args[2]);
        int n = 0;
        for (Player p : players(sender, args[1])) {
            Menu open = menuOf(p);
            if (open != null && open.title.equals(title)) {
                for (var it : items) {
                    if (it.getKey() < open.inventory.getSize()) {
                        open.inventory.setItem(it.getKey(), it.getValue());
                    }
                }
                n++;
            }
        }
        sender.sendMessage("Menu: " + n + " players");
        return true;
    }

    @EventHandler
    public void onLoaded(PlayerClientLoadedWorldEvent ev) {             // the client left "Loading terrain" (#3889)
        getLogger().info(ev.getPlayer().getName() + " loaded the world");   // mc_shot.Client.wait_loaded: keys go to the game
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent ev) {                           // the view of one replay player (#1302)
        for (UUID u : hidden.keySet()) {
            Entity e = Bukkit.getEntity(u);
            if (e != null && hiddenFor(ev.getPlayer(), u)) {
                see(ev.getPlayer(), e, false);
            }
        }
    }

    /** Hide or show e and its riders (Passengers) for p: the UUID of a unit is its root entity (the boat of a ship,
     * the mount of a war elephant), and Player#hideEntity does not hide the riders (#3674). */
    private void see(Player p, Entity e, boolean show) {
        if (show) {
            p.showEntity(this, e);
        } else {
            p.hideEntity(this, e);
        }
        for (Entity r : e.getPassengers()) {
            see(p, r, show);
        }
    }

    /** True when the unit of entity e is hidden for p: the hide names the root vehicle of a rider (#3674). */
    boolean hiddenFor(Player p, Entity e) {
        while (e.getVehicle() != null && !hidden.containsKey(e.getUniqueId())) {
            e = e.getVehicle();
        }
        return hiddenFor(p, e.getUniqueId());
    }

    /** A hide of the team of the player, or of all players (a player with no team yet: each hide, the replay). */
    private boolean hiddenFor(Player p, UUID u) {
        var teams = hidden.get(u);
        if (teams == null) {
            return false;
        }
        Team t = Bukkit.getScoreboardManager().getMainScoreboard().getEntryTeam(p.getName());
        return teams.contains(ALL) || t == null || teams.contains(t.getName());
    }

    /** The team T of a selector with team=T, else ALL (no team, or team=!T). */
    private static String selectorTeam(String selector) {
        int i = selector.indexOf("team=");
        if (i < 0) {
            return ALL;
        }
        String t = selector.substring(i + 5).split("[,\\]]", 2)[0];
        return t.isEmpty() || t.startsWith("!") ? ALL : t;
    }

    @EventHandler
    public void onLeftClick(PlayerInteractEvent ev) {                  // deselect (#1788)
        if ((ev.getAction() == Action.LEFT_CLICK_AIR || ev.getAction() == Action.LEFT_CLICK_BLOCK)
                && commandStick(ev.getPlayer().getInventory().getItemInMainHand())) {
            ev.setCancelled(true);                                     // creative mode: no broken block
            leftClick(ev.getPlayer());
        }
    }

    @EventHandler
    public void onMenuClick(InventoryClickEvent ev) {
        if (!(ev.getView().getTopInventory().getHolder(false) instanceof Menu)) {
            return;
        }
        ev.setCancelled(true);                                         // also shift clicks from the own inventory
        int slot = ev.getRawSlot();
        if (slot >= 0 && slot < ev.getView().getTopInventory().getSize() && ev.getCurrentItem() != null
                && !ev.getCurrentItem().isEmpty()) {
            menuScore().getScore(ev.getWhoClicked().getName()).setScore(ev.isShiftClick() ? -(slot + 1)
                    : ev.getClick() == ClickType.RIGHT ? slot + 1 + MENU_RIGHT : slot + 1);
        }
    }

    @EventHandler
    public void onMenuDrag(InventoryDragEvent ev) {
        if (ev.getView().getTopInventory().getHolder(false) instanceof Menu) {
            ev.setCancelled(true);
        }
    }

    @Override
    public void onEnable() {
        Bukkit.getScheduler().runTaskTimer(this, this::follow, 2L, 2L);
        Bukkit.getScheduler().runTaskTimer(this, camera::tick, 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, this::steer, 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, ghost::tick, 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, border::tick, 4L, 4L);
        Bukkit.getScheduler().runTaskTimer(this, this::siege, 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, this::carts, 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, this::throwAxes, 2L, 2L);
        Bukkit.getScheduler().runTaskTimer(this, this::meleeVolleys, 2L, 2L);
        Bukkit.getScheduler().runTaskTimer(this, this::burn, 20L, 20L);
        Bukkit.getScheduler().runTaskTimer(this, () -> dots.tick(this::dotHurt), Dot.STEP, Dot.STEP);
        Bukkit.getScheduler().runTaskTimer(this, this::unhit, 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, () -> abilities.forEach(ab -> ab.tick(this)), 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, this::speedCharge, 2L, 2L);
        Bukkit.getScheduler().runTaskTimer(this, this::watch, 20L, 20L);
        Bukkit.getScheduler().runTaskTimer(this, this::towers, 2L, 2L);
        Bukkit.getScheduler().runTaskTimer(this, this::hold, 4L, 4L);
        Bukkit.getScheduler().runTaskTimer(this, gates::tick, Gates.PERIOD, Gates.PERIOD);
        Bukkit.getScheduler().runTaskTimer(this, sight::tick, Sight.PERIOD, Sight.PERIOD);
        Bukkit.getPluginManager().registerEvents(this, this);
        Bukkit.getPluginManager().registerEvents(cheats, this);
        Bukkit.getPluginManager().registerEvents(chatName, this);
        Bukkit.getPluginManager().registerEvents(specChat, this);
        Bukkit.getPluginManager().registerEvents(teamChat, this);
        Bukkit.getPluginManager().registerEvents(deaths, this);
        Bukkit.getPluginManager().registerEvents(mapTable, this);
        Bukkit.getPluginManager().registerEvents(viewer, this);
        Bukkit.getPluginManager().registerEvents(cameraMode, this);
    }

    @EventHandler(ignoreCancelled = true)
    public void onHit(EntityDamageByEntityEvent ev) {
        Entity from = ev.getDamager();
        if (from instanceof Player p && commandStick(p.getInventory().getItemInMainHand())) {
            ev.setCancelled(true);                                     // a left click on a unit deselects (#1788)
            leftClick(p);
            return;
        }
        if (from instanceof Projectile p && p.getShooter() instanceof Entity shooter) {
            from = shooter;
            Range r = ranges.get(shooter.getUniqueId());
            if (r != null && r.pass > 0 && !r.siege) {      // the chakram: RangeGoal gave the damage at the throw (#1713)
                ev.setCancelled(true);
                p.remove();
                return;
            }
        }
        Stats a = stats.get(from.getUniqueId()), t = stats.get(ev.getEntity().getUniqueId());
        Building b = buildings.get(ev.getEntity().getUniqueId());
        Building fort = ev.getDamager() instanceof Projectile ? buildings.get(from.getUniqueId()) : null;
        if (fort != null && b == null && !sameTeam(from, ev.getEntity())) {
            a = fort.stats;                                   // the arrow of a town center or castle on a unit (#1111)
        } else if (buildings.containsKey(from.getUniqueId()) || b != null) {
            ev.setCancelled(true);
            if (a != null && b != null && !(ev.getDamager() instanceof Projectile) && ready(from, a)) {   // RangeGoal counts a shot
                struck(from);
                hit(ev.getEntity(), b, damage(a, b, from, ev.getEntity()), from);
                hitEffect(ev.getEntity(), b, from);
                alerts.hit(ev.getEntity(), true, from);
            }
            return;
        }
        Entity hurt = ev.getEntity();
        if (hurt.getVehicle() instanceof LivingEntity horse && stats.containsKey(horse.getUniqueId())) {
            hurt = horse;                        // a mounted unit has the hit points of its horse (#732)
            t = stats.get(horse.getUniqueId());
        }
        if (a == null || t == null || !(hurt instanceof LivingEntity victim)) {
            return;
        }
        ev.setCancelled(true);
        Dodge dodge = dodges.getOrDefault(ev.getEntity().getUniqueId(), dodges.get(hurt.getUniqueId()));
        Blast blast = null;                                // the blast of a charged hit (#4544)
        if (ev.getDamager() instanceof Projectile p && dodge != null && !dodge.melee && dodge.take()) {
            p.remove();                                      // a Shrivamsha Rider dodges it (#4399)
            return;
        }
        if (ev.getDamager() instanceof Projectile p) {
            for (Ability ab : abilities) {
                if (ab.shot(this, p, from, ev.getEntity(), victim, a)) {
                    return;                                  // a Hussite Wagon (#4507)
                }
            }
        }
        Range sr = ranges.get(from.getUniqueId());
        if (ev.getDamager() instanceof Projectile p && (sr == null || !sr.siege) && fort == null
                && ThreadLocalRandom.current().nextDouble() >= accuracy.getOrDefault(from.getUniqueId(), 1.0)) {
            p.remove();                                      // AoE2 accuracy of an arrow (an Arambai, #4549): a miss
            double[] miss = misses.get(from.getUniqueId());
            if (miss != null && near(from, hurt, miss[1]) instanceof LivingEntity n) {
                harm(n, stats.get(n.getUniqueId()), volley(p, a), from, miss[0]);   // it hurts a unit near the target
            }
            return;
        }
        if (!(ev.getDamager() instanceof Projectile)) {      // a melee hit: once per AoE2 reload (#848)
            if (!ready(from, a)) {
                return;
            }
            struck(from);
            if (dodge != null && dodge.melee && dodge.take()) {
                return;                                      // an Iron Pagoda ignores the melee hit (#4465)
            }
            Stats plain = a;
            a = charged(from, a);                            // a charge attack (Comitatenses, #4370)
            blast = a != plain ? meleeBlasts.get(from.getUniqueId()) : null;
        }
        if (ev.getDamager() instanceof Projectile p) {     // a cancelled hit lets the arrow fly on: one hit per arrow
            p.remove();
            a = volley(p, a);                                // an extra arrow of a volley (#2379)
            for (Ability ab : abilities) {
                a = ab.hit(this, from, victim, a);           // a charged shot (Bolas Rider, #4548)
            }
        }
        double dealt = harm(victim, t, a, fort != null ? ev.getDamager() : from);   // a unit does not attack back at a building
        if (fort != null) {
            dots.start(from, victim, t.classes());           // harm() has the arrow, not the building (Curare, #4641)
        }
        if (fort == null && sunders.get(from.getUniqueId()) instanceof Integer n && stats.get(hurt.getUniqueId()) == t) {
            stats.put(hurt.getUniqueId(), sunder(t, n));      // an Obuch lowers the armor of its target (#4466)
        }
        double[] through = fort != null ? fortPass.get(from.getUniqueId()) : null;
        if (through != null && through[0] > 0 && from instanceof Mob slime) {   // Svan Towers: hurts the units behind (#4282)
            pass(slime, victim, fort.range + through[0], a, from, through[1]);
        }
        if (t.reflect > 0 && !(ev.getDamager() instanceof Projectile) && body(from) instanceof LivingEntity attacker
                && !attacker.isDead()) {                      // Lamellar Armor: the attacker takes a part back (#4332)
            attacker.playHurtAnimation(0);
            attacker.setHealth(Math.max(0, attacker.getHealth() - dealt * t.reflect));   // no armor (AoE2 DE wiki)
            nameLine(attacker);
        }
        if (!(ev.getDamager() instanceof Projectile)) {
            for (Ability ab : abilities) {
                ab.melee(this, from, a, hurt, ev.getEntity());   // an elephant (#4397)
            }
            trample(from, a, hurt, ev.getEntity(), blast);    // the charged hit of an Urumi Swordsman (#4544)
        }
    }

    // A random other enemy unit of from with AoE2 values within blocks of the unit hurt, or null: the unit that a
    // missed shot hits (#4549). A mounted unit has the hit points of its horse (#732): only the horse counts.
    private LivingEntity near(Entity from, Entity hurt, double blocks) {
        List<LivingEntity> all = new ArrayList<>();
        for (Entity o : hurt.getNearbyEntities(blocks, blocks, blocks)) {
            if (o instanceof LivingEntity le && le.isValid() && !le.isDead() && le != from && o.getVehicle() != hurt
                    && stats.containsKey(o.getUniqueId()) && !buildings.containsKey(o.getUniqueId())
                    && !sameTeam(from, o) && o.getLocation().distance(hurt.getLocation()) <= blocks) {
                all.add(le);
            }
        }
        return all.isEmpty() ? null : all.get(ThreadLocalRandom.current().nextInt(all.size()));
    }

    // AoE2 trample damage (#4397, AoE2 DE wiki "Trample damage"): after a melee hit of a unit of aoe trample, each other
    // enemy unit with AoE2 values within its blocks of the target takes max(1, round(part × the AoE2 damage on it)), or
    // the fixed damage less its melee armor (at least 1; ignore: a negative armor only). Not the own or allied units.
    // A mounted unit has the hit points of its horse (#732): only the horse counts.
    void trample(Entity from, Stats a, Entity hurt, Entity target, Blast tr) {
        if (tr == null || tr.blocks() <= 0) {
            return;
        }
        Location at = hurt.getLocation();
        double r = tr.blocks();
        for (Entity e : at.getWorld().getNearbyEntities(at, r, r, r)) {
            if (e instanceof LivingEntity le && le.isValid() && !le.isDead() && le != hurt && le != target && le != from
                    && le != from.getVehicle() && stats.containsKey(le.getUniqueId()) && !buildings.containsKey(le.getUniqueId())
                    && !(le.getVehicle() instanceof LivingEntity v && stats.containsKey(v.getUniqueId()))
                    && !sameTeam(from, le) && !friendlyFire(from, le) && le.getLocation().distanceSquared(at) <= r * r) {
                Stats t2 = stats.get(le.getUniqueId());
                double full = Math.max(1, a.damage(t2, rage(a, from)) * elevation(from, le));   // the rule of harm
                double hit = tr.damage() <= 0 ? Math.max(1, Math.round(tr.part() * full))
                        : tr.ignore() ? tr.damage() - Math.min(0, t2.melee()) : Math.max(1, tr.damage() - t2.melee());
                harm(le, t2, a, from, hit / full);
            }
        }
        at.getWorld().spawnParticle(Particle.SWEEP_ATTACK, at.clone().add(0, 1, 0), 1);
    }

    // The entity with the hit points of unit e: the horse of a rider (#732), else e.
    Entity body(Entity e) {
        return e != null && e.getVehicle() instanceof LivingEntity horse && stats.containsKey(horse.getUniqueId()) ? horse : e;
    }

    // The attack more of a hit of unit e with the values a (Hamask, #4332): rage for each 10 % of its lost hit points.
    private int rage(Stats a, Entity e) {
        if (a.rage <= 0 || !(body(e) instanceof LivingEntity le) || le.getAttribute(Attribute.MAX_HEALTH) == null) {
            return bonus(e) + pack(e);
        }
        double max = le.getAttribute(Attribute.MAX_HEALTH).getValue();
        return a.rage * (int) Math.floor(Math.max(0, 1 - le.getHealth() / max) * 10 + 1e-9) + bonus(e) + pack(e);
    }

    // The attack more of unit e near its own units (aoe pack, the Monaspa, #4469): the type tag sits on the rider of a
    // mounted unit, so the tagged entities count once and the horse of e and e itself not at all.
    private int pack(Entity e) {
        Pack p = e == null ? null : packs.get(e.getUniqueId());
        if (p == null) {
            return 0;
        }
        Entity me = body(e), rider = me.getPassengers().isEmpty() ? me : me.getPassengers().get(0);
        String own = side(rider);
        if (own == null) {
            return 0;
        }
        int n = 0;
        for (Entity o : me.getNearbyEntities(p.blocks, p.blocks, p.blocks)) {
            if (o == e || o == rider || o.getLocation().distance(me.getLocation()) > p.blocks
                    || !own.equals(side(o)) || Collections.disjoint(o.getScoreboardTags(), p.tags)) {
                continue;
            }
            n++;
        }
        return Math.min(p.max, n / p.per);
    }

    // The attack more of unit e of its abilities (the Jaguar Warrior, #4467).
    private int bonus(Entity e) {
        int n = 0;
        for (Ability ab : abilities) {
            n += ab.attack(e);
        }
        return n;
    }

    // A fight between two samples of aoe where (#1169): tools/replay_drift.py does not count the moves of a fight as
    // "stray". A mounted unit: the rider and its horse.
    private void fight(Entity e) {
        Entity u = e.getVehicle() == null ? e : e.getVehicle();
        fought.add(u.getUniqueId());
        u.getPassengers().forEach(p -> fought.add(p.getUniqueId()));
    }

    @EventHandler(ignoreCancelled = true)
    public void onTarget(EntityTargetEvent ev) {
        if (ev.getTarget() != null && ev.getEntity() instanceof Mob) {
            fight(ev.getEntity());
        }
    }

    // The AoE2 damage of attacker values a on the victim with values t (#514), and the attack back.
    // The scoreboard tag aoe2mc.hit for 10 ticks after an AoE2 hit, as HurtTime: setHealth does not set the hurt time,
    // and the trigger condition "Object Attacked" tests it (predicate aoe2mc:attacked, #3085). The passengers too: the
    // plugin hurts the mount of a rider, and the tag aoe2mc.r<ref> is on the rider.
    private final Map<Entity, Integer> hits = new HashMap<>();

    private void hitTag(Entity victim) {
        for (Entity e : concat(victim, victim.getPassengers())) {
            e.addScoreboardTag("aoe2mc.hit");
            hits.put(e, Bukkit.getCurrentTick() + 10);
        }
    }

    private static List<Entity> concat(Entity e, List<Entity> more) {
        List<Entity> all = new ArrayList<>(more);
        all.add(e);
        return all;
    }

    private void unhit() {
        int now = Bukkit.getCurrentTick();
        hits.entrySet().removeIf(h -> {
            if (h.getValue() > now && h.getKey().isValid()) {
                return false;
            }
            h.getKey().removeScoreboardTag("aoe2mc.hit");
            return true;
        });
    }

    // The values t with the melee and the pierce armor each n less, down to 0 (aoe sunder, #4466); a negative armor stays.
    private static Stats sunder(Stats t, int n) {
        return new Stats(t.attack, t.melee > 0 ? Math.max(0, t.melee - n) : t.melee,
                t.pierce > 0 ? Math.max(0, t.pierce - n) : t.pierce, t.ranged, t.pierces, t.classes, t.bonus, t.reload,
                t.taken, t.friendly, t.less, t.ignores, t.rage, t.reflect);
    }

    // The speed charge (aoe speedcharge, #4545): vanilla has no "faster near the target" rule, so the plugin reads the
    // distance to the target and sets a speed modifier on the mob that walks (the horse of a mounted unit). Below min
    // blocks (the hit) the modifier goes, as the charge "dissipates once impact is made" (AoE2 wiki, "Samurai").
    private void speedCharge() {
        speedCharges.entrySet().removeIf(en -> {
            if (!(Bukkit.getEntity(en.getKey()) instanceof Mob m) || !m.isValid()) {
                return true;
            }
            double[] c = en.getValue();
            LivingEntity t = target(m);
            double d = t == null || t.getWorld() != m.getWorld() ? -1 : m.getLocation().distance(t.getLocation());
            boolean on = d >= c[1] && d <= c[2];
            LivingEntity walker = m.getVehicle() instanceof LivingEntity v ? v : m;
            AttributeInstance speed = walker.getAttribute(Attribute.MOVEMENT_SPEED);
            if (speed != null && on != (speed.getModifier(CHARGE_SPEED) != null)) {
                speed.removeModifier(CHARGE_SPEED);
                if (on) {
                    speed.addTransientModifier(new AttributeModifier(CHARGE_SPEED, c[0],
                            AttributeModifier.Operation.ADD_SCALAR));
                }
            }
            return false;
        });
    }

    private double harm(LivingEntity victim, Stats t, Stats a, Entity from) {
        return harm(victim, t, a, from, 1.0);
    }

    // part: the part of the AoE2 damage (0.5 for a unit behind the target of a Scorpion bolt, #1401). It gives the damage.
    double harm(LivingEntity victim, Stats t, Stats a, Entity from, double part) {
        a = vs(from, a);                                  // a unit is the target: the anti-unit mode (#4505)
        alerts.hit(victim, false, from);                  // before the hit: a unit that dies of it is attacked too
        fight(victim);
        fight(from);
        victim.playHurtAnimation(0);
        hitTag(victim);
        double before = victim.getHealth();
        double damage = Math.max(1, a.damage(t, rage(a, from)) * (from == null ? 1 : elevation(from, victim)));   // AoE2: after the armor
        victim.setHealth(Math.max(0, before - damage * part));     // 0 kills it
        dots.start(from, victim, t.classes());                     // Curare (#4339)
        gold(from, victim, a);
        if (before > 0 && victim.getHealth() <= 0) {
            kill(from, a, t);
            unitKill(from, victim, a);
            if (from != null) {
                abilities.forEach(ab -> ab.killed(from));           // a Jaguar Warrior gets stronger (#4467)
            }
        }
        nameLine(victim);
        if (victim.getHealth() > 0 && from instanceof LivingEntity attacker && !attacker.isDead()) {   // a detonation
            attackBack(victim, attacker, t);
        }
        return damage * part;
    }

    // A unit with the tag aoe2mc.gold.N (N gold per 100 AoE2 minutes while it attacks enemy units: the Varangian Guard,
    // the Keshik, game/spoils.py, #2376) that hits an enemy unit adds N × its reload ticks to the score aoe_attack_gold of its side.
    // A hit on a building gives no gold: it does not come here.
    private static void gold(Entity from, Entity victim, Stats a) {
        String side = from == null || sameTeam(from, victim) ? null : side(from);
        for (String tag : side == null ? Set.<String>of() : from.getScoreboardTags()) {
            if (tag.startsWith("aoe2mc.gold.")) {
                Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
                Objective o = sb.getObjective("aoe_attack_gold");
                o = o != null ? o : sb.registerNewObjective("aoe_attack_gold", Criteria.DUMMY, Component.text("Attack gold"));
                var score = o.getScore(side);
                score.setScore(score.getScore() + Integer.parseInt(tag.substring(12)) * a.reload());
            }
        }
    }

    // A mounted unit that kills a military unit gives its side one point in aoe_mounted_kills: the Mapuche gold
    // (game/spoils.py, #2271). Mounted: the classes of civs.mounted; military: an attack and an armor class (no
    // villager, monk, trade unit or fishing ship). Vanilla has no killer of a mob: the plugin sees the last hit.
    private static void kill(Entity from, Stats a, Stats t) {
        if (from == null) {
            return;
        }
        String side = side(from) == null && from.getVehicle() != null ? side(from.getVehicle()) : side(from);   // a rider
        if (side == null || t.attack() <= 0 || t.classes().isEmpty()
                || a.classes().stream().noneMatch(c -> c.equals("cavalry") || c.equals("camel") || c.equals("elephant"))) {
            return;
        }
        Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
        Objective o = sb.getObjective("aoe_mounted_kills");
        o = o != null ? o : sb.registerNewObjective("aoe_mounted_kills", Criteria.DUMMY, Component.text("Mounted kills"));
        var score = o.getScore(side);
        score.setScore(score.getScore() + 1);
    }

    // An infantry or cavalry unit that kills an enemy unit gives its side one point in aoe_unit_kills: the gold of the
    // Athenian Military Policy (game/spoils.py, #2512). AoE2 wiki "Military Policy": no gold for a King (tag
    // aoe2mc.king) or a trade unit (tag aoe2mc.trade, spoils.tag_command); no point for a Gaia animal (no side).
    private static void unitKill(Entity from, Entity victim, Stats a) {
        if (from == null) {
            return;
        }
        String side = side(from) == null && from.getVehicle() != null ? side(from.getVehicle()) : side(from);   // a rider
        String foe = side(victim) == null && victim.getVehicle() != null ? side(victim.getVehicle()) : side(victim);
        if (side == null || foe == null || sameTeam(from, victim) || victim.getScoreboardTags().contains("aoe2mc.king")
                || victim.getScoreboardTags().contains("aoe2mc.trade")
                || a.classes().stream().noneMatch(c -> c.equals("infantry") || c.equals("cavalry"))) {
            return;
        }
        Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
        Objective o = sb.getObjective("aoe_unit_kills");
        o = o != null ? o : sb.registerNewObjective("aoe_unit_kills", Criteria.DUMMY, Component.text("Unit kills"));
        var score = o.getScore(side);
        score.setScore(score.getScore() + 1);
    }

    // The AoE2 default stance (#733): a military unit without an order and without a target attacks its attacker.
    // A mounted unit: the horse has the order, the rider the target (#710).
    // The crew of a siege unit keeps NoAI: unit() would turn on its brain for good (a warden digs, #3016). watch()
    // gives the idle siege unit its target with the siege rules (#1820).
    private void attackBack(LivingEntity victim, LivingEntity attacker, Stats t) {
        if (victim instanceof Mob mob && !(mob.getVehicle() instanceof Minecart) && idle(mob, t) && !sameTeam(mob, attacker)
                && !attacker.getScoreboardTags().contains(NO_TARGET)
                && mob.getLocation().distanceSquared(attacker.getLocation()) <= Math.pow(stanceRange(mob), 2)) {
            engage(mob, attacker);
            Mob fighter = rider(mob) != null ? rider(mob) : mob;      // it turns and swings first: its first hit
            lastHit.putIfAbsent(fighter.getUniqueId(), Bukkit.getCurrentTick() - t.reload() / 2);   // after half a reload
        }
    }

    // A military unit without an order and without a target: the units of the AoE2 default stance (#733, #775),
    // not with the stance "no attack" (#1104).
    private boolean idle(Mob mob, Stats t) {
        Mob fighter = rider(mob) != null ? rider(mob) : mob;
        return t != null && (!t.classes().isEmpty() || sights.containsKey(mob.getUniqueId())) && t.attack() > 0
                && !orders.containsKey(mob.getUniqueId())
                && (target(fighter) == null || !target(fighter).isValid()) && !stance(mob).equals("no_attack");
    }

    // The stance of a unit, of its rider or of its horse: the selector can name each one (#1104).
    private String stance(Entity e) {
        String s = stances.get(e.getUniqueId());
        if (s == null && rider(e) != null) {
            s = stances.get(rider(e).getUniqueId());
        }
        if (s == null && e.getVehicle() != null) {
            s = stances.get(e.getVehicle().getUniqueId());
        }
        if (s == null && e.getScoreboardTags().contains(CARRIER) && !e.getPassengers().isEmpty()) {
            s = stances.get(e.getPassengers().get(0).getUniqueId());   // a carrier: the stance of its siege unit (#1820)
        }
        return s == null ? "aggressive" : s;
    }

    // The blocks to an enemy that a unit attacks without an order: no limit, with stand ground its range (#1104).
    private double stanceRange(Entity mob) {
        if (!stance(mob).equals("stand_ground")) {
            return Double.MAX_VALUE;
        }
        Entity fighter = rider(mob) != null ? rider(mob) : mob;
        Range r = ranges.get(fighter.getUniqueId());
        if (r == null && fighter.getScoreboardTags().contains(CARRIER) && !fighter.getPassengers().isEmpty()) {
            r = ranges.get(fighter.getPassengers().get(0).getUniqueId());   // a carrier: the range of its siege unit
        }
        return r != null ? r.blocks() : MELEE;
    }

    private void engage(Mob mob, LivingEntity enemy) {
        Mob fighter = rider(mob) != null ? rider(mob) : mob;
        if (fighter != mob) {
            unit(mob).getPathfinder().stopPathfinding();
        }
        reach(fighter, enemy.getLocation());
        setTarget(unit(fighter), enemy);
        fight(mob);                                    // Mob#setTarget of a plugin fires no EntityTargetEvent (#1334)
        if (stance(mob).equals("stand_ground")) {
            held.add(fighter.getUniqueId());
        } else if (stance(mob).equals("defensive")) {
            posts.putIfAbsent(mob.getUniqueId(), mob.getLocation());
        }
    }

    // Stand ground (#1104): a unit drops a target of its own that went out of its range, and stays.
    private void hold() {
        held.removeIf(id -> {
            if (!(Bukkit.getEntity(id) instanceof Mob f) || !f.isValid()) {
                return true;
            }
            Mob mob = f.getVehicle() instanceof Mob h ? h : f;
            LivingEntity t = target(f);
            if (t != null && t.isValid() && !t.isDead()
                    && f.getLocation().distanceSquared(t.getLocation()) <= Math.pow(stanceRange(mob), 2)) {
                return false;
            }
            setTarget(f, null);
            f.getPathfinder().stopPathfinding();
            return true;
        });
        posts.entrySet().removeIf(en -> {      // defensive (#1105): back to the place past the chase distance
            if (!(Bukkit.getEntity(en.getKey()) instanceof Mob mob) || !mob.isValid() || orders.containsKey(en.getKey())) {
                return true;
            }
            Mob f = rider(mob) != null ? rider(mob) : mob;
            Range r = ranges.get(f.getUniqueId());
            LivingEntity t = target(f);
            double far = Math.pow((r != null ? r.blocks() : MELEE) + CHASE, 2);
            double gone = Math.pow(Math.max(r != null ? r.blocks() : MELEE, sights.getOrDefault(en.getKey(), 0.0))
                    + CHASE, 2);                       // the target left its sight + CHASE: back too (#1968)
            if (t != null && t.isValid() && !t.isDead() && mob.getLocation().distanceSquared(en.getValue()) <= far
                    && t.getLocation().distanceSquared(en.getValue()) <= gone) {
                return false;
            }
            setTarget(f, null);
            f.getPathfinder().stopPathfinding();
            reach(mob, en.getValue());
            mob.getPathfinder().moveTo(en.getValue(), 1.0);
            orders.put(mob.getUniqueId(), new Order(en.getValue(), 1.0));
            return true;
        });
    }

    // Each second: an idle unit with a line of sight attacks the nearest unit of another team in it (#775). Only
    // units with AoE2 values are enemies: Gaia animals, players, building targets and garrisoned units are not (#1285).
    // A unit with a building mode (aoe sight ... only|first, #1820) also takes the nearest enemy building in its sight,
    // as in AoE2 (wiki "Siege unit (Age of Empires II)"): "only" (the Battering Ram line, the Trebuchet) takes no
    // units, "first" (the Armored Elephant line, the Cannon Galleon line) takes a building before a unit. A siege unit
    // (a minecart) looks with its crew; a siege unit with range 0 (a packed trebuchet) and a unit that cannot walk
    // (an unpacked trebuchet: speed 0) take only a target in their range.
    private void watch() {
        sights.entrySet().removeIf(en -> {
            Entity e = Bukkit.getEntity(en.getKey());
            if (e == null || !e.isValid()) {
                if (e == null || e.isDead()) {                        // an unloaded unit keeps its sight
                    modes.remove(en.getKey());
                    return true;
                }
                return false;
            }
            if (e instanceof Mob m && target(rider(m) != null ? rider(m) : m) instanceof LivingEntity t
                    && t.isInvulnerable() && stats.containsKey(t.getUniqueId())) {   // it went into a building (#1285)
                Mob f = rider(m) != null ? rider(m) : m;
                setTarget(f, null);
                f.getPathfinder().stopPathfinding();
            }
            Entity crew = e instanceof Minecart && !e.getPassengers().isEmpty() ? e.getPassengers().get(0) : e;
            Mob mob = e instanceof Minecart cart ? carrier(cart, false) : e instanceof Mob m ? m : null;
            Stats st = stats.get(crew.getUniqueId());
            if (mob != null ? !idle(mob, st) : !(e instanceof Minecart && st != null && st.attack() > 0
                    && !stance(e).equals("no_attack"))) {           // a minecart without a carrier: no order yet
                return false;
            }
            double r = Math.min(en.getValue(), stanceRange(mob != null ? mob : e));
            Range range = ranges.get(e.getUniqueId());
            if (e instanceof Minecart && range != null && range.siege()) {
                AttributeInstance speed = mob == null ? null : mob.getAttribute(Attribute.MOVEMENT_SPEED);
                r = speed != null && speed.getBaseValue() <= 0 || range.blocks() <= 0 ? Math.min(r, range.blocks()) : r;
                if (r <= 0) {
                    return false;
                }
            }
            String mode = modes.get(e.getUniqueId());
            LivingEntity best = mode != null ? building(e, crew, r) : null;
            double bestD = r * r;
            for (Entity o : best != null || "only".equals(mode) ? List.<Entity>of() : e.getNearbyEntities(r, r, r)) {
                if (o instanceof LivingEntity le && le.isValid() && stats.containsKey(le.getUniqueId())
                        && !buildings.containsKey(le.getUniqueId()) && !calm(crew, le) && !le.isInvulnerable()
                        && !(le.getVehicle() instanceof LivingEntity v && stats.containsKey(v.getUniqueId()))   // a crew counts (#3015)
                        && !(mob != null && afloat(le) && !(mob.getVehicle() instanceof Boat)
                            && !ranged(rider(mob) != null ? rider(mob) : mob))   // a land melee unit cannot reach a ship (#1658)
                        && e.getLocation().distanceSquared(le.getLocation()) <= bestD) {
                    best = le;
                    bestD = e.getLocation().distanceSquared(le.getLocation());
                }
            }
            if (best != null) {
                engage(mob != null ? mob : unit(e), best);
            }
            return false;
        });
    }

    // The target of the nearest enemy building whose box is within r blocks of unit e (#1820): no Gaia building, no
    // building of a neutral player. crew: the entity with the team of a siege unit.
    private LivingEntity building(Entity e, Entity crew, double r) {
        LivingEntity best = null;
        double bestD = r * r;
        Location l = e.getLocation();
        for (var en : buildings.entrySet()) {
            int[] b = en.getValue().b();
            double dx = Math.max(0, Math.max(b[0] - l.getX(), l.getX() - b[3] - 1));
            double dz = Math.max(0, Math.max(b[2] - l.getZ(), l.getZ() - b[5] - 1));
            if (dx * dx + dz * dz <= bestD && Bukkit.getEntity(en.getKey()) instanceof LivingEntity t && t.isValid()
                    && t.getWorld() == e.getWorld() && side(t) != null && !calm(crew, t) && !calm(e, t)) {
                best = t;
                bestD = dx * dx + dz * dz;
            }
        }
        return best;
    }

    @EventHandler
    public void onDeath(EntityDeathEvent ev) {               // the rider dies with its horse, else it stays (#732)
        stances.remove(ev.getEntity().getUniqueId());
        if (ev.getEntity().getScoreboardTags().contains("aoe2mc.on_death")) {   // a Konnik (#4471): game/train.py fell()
            ev.getEntity().getWorld().spawn(ev.getEntity().getLocation(), Marker.class,   // summons the new unit here
                    m -> m.addScoreboardTag("aoe2mc.fell." + ev.getEntity().getUniqueId()));
        }
        throwers.remove(ev.getEntity().getUniqueId());
        axes.remove(ev.getEntity().getUniqueId());
        afterBlasts.remove(ev.getEntity().getUniqueId());
        Charge blast = detonations.remove(ev.getEntity().getUniqueId());
        if (blast != null) {                                     // Incendiaries: the fire ship explodes (#2165)
            burst(ev.getEntity(), ev.getEntity().getLocation(), blast, spare.remove(ev.getEntity().getUniqueId()));
        }
        if (stats.containsKey(ev.getEntity().getUniqueId()) && ev.getEntity().getVehicle() instanceof Boat boat) {
            ev.getDrops().clear();                               // the crew of a ship at 0 hit points: the ship sinks (#1386)
            boat.getPassengers().stream().filter(p -> p != ev.getEntity() && !(p instanceof Player)).forEach(Entity::remove);
            boat.remove();
        }
        if (stats.containsKey(ev.getEntity().getUniqueId()) && ev.getEntity().getVehicle() instanceof Minecart cart) {
            Mob carrier = carrier(cart, false);              // a dead siege unit leaves no minecart and no carrier (#3017)
            cart.remove();
            if (carrier != null) {
                carrier.remove();
            }
        }
        if (stats.containsKey(ev.getEntity().getUniqueId())) {
            for (Entity p : ev.getEntity().getPassengers()) {
                if (p instanceof LivingEntity r && stats.containsKey(r.getUniqueId())) {
                    r.setHealth(0);
                } else if (!(p instanceof LivingEntity) && !(p instanceof Player)) {
                    p.remove();                              // the cart of a War Wagon: no item display stays (#3017)
                }
            }
        }
    }

    // A hit on the boat of a ship or the minecart of a siege unit goes to its crew, which has the AoE2 values (#1386,
    // #3014): the vanilla vehicle breaks after a few arrows and drops an item. An arrow that hits it hurts the crew
    // with the AoE2 damage of its shooter.
    @EventHandler(ignoreCancelled = true)
    public void onBoatHit(VehicleDamageEvent ev) {
        if (!(crew(ev.getVehicle()) instanceof LivingEntity c) || !stats.containsKey(c.getUniqueId())) {
            return;
        }
        ev.setCancelled(true);
        Entity from = ev.getAttacker();
        if (from instanceof Projectile p) {
            p.remove();                                  // one hit per arrow
            from = p.getShooter() instanceof Entity shooter ? shooter : null;
        }
        Stats a = from == null ? null : stats.get(from.getUniqueId());
        Building fort = from == null ? null : buildings.get(from.getUniqueId());
        if (fort != null && ev.getAttacker() instanceof Projectile) {
            a = fort.stats;                                  // the arrow of a tower, castle or town center (#3015)
        } else if (a != null && ev.getAttacker() instanceof Projectile p) {
            a = volley(p, a);                                // an extra arrow of an Armenian galley (#2379)
        }
        if (a != null && c.isValid() && !sameTeam(from, c)) {
            harm(c, stats.get(c.getUniqueId()), a, from);
        }
    }

    @EventHandler(ignoreCancelled = true)
    public void onBoatBreak(VehicleDestroyEvent ev) {       // a ship sinks only at 0 hit points of its crew (#1386, #3014)
        if (crew(ev.getVehicle()) instanceof LivingEntity c && stats.containsKey(c.getUniqueId())) {
            ev.setCancelled(true);
        }
    }

    @EventHandler(ignoreCancelled = true)
    public void onDrown(EntityTransformEvent ev) {           // a unit stays a unit under water: no Drowned (#1658)
        if (ev.getTransformReason() == EntityTransformEvent.TransformReason.DROWNED
                && stats.containsKey(ev.getEntity().getUniqueId())) {
            ev.setCancelled(true);
        }
    }

    @EventHandler(ignoreCancelled = true)
    public void onCombust(EntityCombustEvent ev) {           // the lava cauldron of a blacksmith: an invisible target
        if (buildings.containsKey(ev.getEntity().getUniqueId())   // that burns shows the fire over the footprint (#1526);
                || ev.getEntity().getScoreboardTags().contains(BUILDING)) {   // also before "aoe building" (#4690)
            ev.setCancelled(true);
        }
    }

    @EventHandler(ignoreCancelled = true)
    public void onHurt(EntityDamageEvent ev) {               // suffocation in its walls, fire, fall ...
        Entity e = ev.getEntity();
        if (!(ev instanceof EntityDamageByEntityEvent) && (buildings.containsKey(e.getUniqueId())
                || e.getScoreboardTags().contains(BUILDING))) {       // also a target with no entry yet (#3723)
            ev.setCancelled(true);
        } else if (ev.getCause() == EntityDamageEvent.DamageCause.DROWNING && e.getVehicle() instanceof Boat
                && stats.containsKey(e.getUniqueId())) {
            ev.setCancelled(true);                            // the blaze crew of a fire ship in the rain (#1440)
        } else if (names.containsKey(e.getUniqueId())) {      // the new health is set after the event
            Bukkit.getScheduler().runTask(this, () -> nameLine(e));
        }
    }

    @EventHandler(ignoreCancelled = true)
    public void onSplit(SlimeSplitEvent ev) {                 // the small slimes of a dead target have its name but no
        if (ev.getEntity().getScoreboardTags().contains(BUILDING)) {   // entry: they suffocate in its walls (#3723)
            ev.setCancelled(true);
        }
    }

    @EventHandler(ignoreCancelled = true)
    public void onRegain(EntityRegainHealthEvent ev) {        // a horse heals by itself, an AoE2 unit does not (#850)
        if (ev.getRegainReason() == EntityRegainHealthEvent.RegainReason.REGEN
                && stats.containsKey(ev.getEntity().getUniqueId())) {
            ev.setCancelled(true);
        }
    }

    private static Objective hp() {
        Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
        Objective o = sb.getObjective("aoe_hp");
        return o != null ? o : sb.registerNewObjective("aoe_hp", Criteria.DUMMY, "Hit points");
    }

    // The values a of from in its anti-unit mode (aoe vsunits, the Lou Chuan, #4505): a pierce attack; else a.
    private Stats vs(Entity from, Stats a) {
        VsUnits v = from == null ? null : vsUnits.get(from.getUniqueId());
        return v == null ? a : new Stats(v.attack(), a.melee(), a.pierce(), true, true, a.classes(), v.bonus(), a.reload(),
                a.taken(), a.friendly(), a.less(), a.ignores(), a.rage(), a.reflect());
    }

    // The damage of a hit of a on building b, with the elevation of from over target (#2307)
    private static int damage(Stats a, Building b, Entity from, Entity target) {
        return (int) Math.max(1, Math.round(a.damage(b.stats) * elevation(from, target)));
    }

    // A hit of from on building target b: also its damage over time (Red Cliffs Tactics, #4339)
    private void hit(Entity target, Building b, int damage, Entity from) {
        hit(target, b, damage);
        dots.start(from, target, b.stats().classes());
    }

    // One step of a damage over time (Dot.java, #4339): a building target loses whole hit points, a unit loses the
    // damage with no armor, no hurt animation and no attack back, and its death counts for the attacker.
    private void dotHurt(Entity target, UUID from, double damage, int whole) {
        Building b = buildings.get(target.getUniqueId());
        if (b != null) {
            if (whole > 0) {
                hit(target, b, whole);
            }
            return;
        }
        Stats t = stats.get(target.getUniqueId());
        if (!(target instanceof LivingEntity victim) || t == null || victim.getHealth() <= 0) {
            return;
        }
        victim.setHealth(Math.max(0, victim.getHealth() - damage));     // 0 kills it
        hitTag(victim);
        Entity by = Bukkit.getEntity(from);
        Stats a = stats.get(from);
        if (victim.getHealth() <= 0 && by != null && a != null) {
            kill(by, a, t);
            unitKill(by, victim, a);
            abilities.forEach(ab -> ab.killed(by));                 // a Jaguar Warrior gets stronger (#4467)
        }
        nameLine(victim);
    }

    private void hit(Entity target, Building b, int damage) {
        var score = hp().getScoreFor(target);
        score.setScore(Math.max(0, score.getScore() - damage));
        if (target instanceof LivingEntity le) {
            le.playHurtAnimation(0);
        }
        nameLine(target);
        if (score.getScore() == 0) {                          // the building falls
            buildings.remove(target.getUniqueId());
            wear.remove(target.getUniqueId());
            names.remove(target.getUniqueId());
            label(target, b, null);
            score.resetScore();
            target.remove();
            clear(b.box);
        }
    }

    /** Fill the box "x0 y0 z0 x1 y1 z1" with air in layers of at most MAX_FILL blocks: the server refuses a larger
     *  fill, and a large building at a large tile size has more (#3076; Replay.fill does the same). */
    private static void clear(String box) {
        int[] c = java.util.Arrays.stream(box.trim().split("\\s+")).mapToInt(Integer::parseInt).toArray();
        int x0 = Math.min(c[0], c[3]), x1 = Math.max(c[0], c[3]), y0 = Math.min(c[1], c[4]), y1 = Math.max(c[1], c[4]);
        int z0 = Math.min(c[2], c[5]), z1 = Math.max(c[2], c[5]);
        int step = Math.max(1, MAX_FILL / ((x1 - x0 + 1) * (z1 - z0 + 1)));
        for (int y = y0; y <= y1; y += step) {
            Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "fill " + x0 + " " + y + " " + z0 + " " + x1 + " "
                + Math.min(y + step - 1, y1) + " " + z1 + " minecraft:air");
        }
    }

    /** The roof block over column (x, z) of a building, or null when the column is empty (#660). */
    private static org.bukkit.block.Block roof(Entity target, int x, int z) {
        var block = target.getWorld().getHighestBlockAt(x, z, HeightMap.MOTION_BLOCKING);
        return block.getType().isAir() ? null : block;
    }

    /** Block particles and the hit sound of the block at the point of the building next to the attacker (#660). */
    private static void hitEffect(Entity target, Building b, Entity from) {
        if (!target.isValid()) {                              // the building fell
            return;
        }
        var at = from.getLocation().add(0, 1, 0);
        int x = Math.clamp(at.getBlockX(), b.b[0], b.b[3]), z = Math.clamp(at.getBlockZ(), b.b[2], b.b[5]);
        int y = Math.clamp(at.getBlockY(), b.b[1], b.b[4]);
        var block = target.getWorld().getBlockAt(x, y, z);
        if (block.getType().isAir() || block.getType() == Material.BARRIER) {
            block = roof(target, (b.b[0] + b.b[3]) / 2, (b.b[2] + b.b[5]) / 2);
        }
        if (block == null) {
            return;
        }
        BlockData data = block.getBlockData();
        var loc = new Location(target.getWorld(), x + 0.5, Math.min(y, block.getY()) + 0.5, z + 0.5);
        target.getWorld().spawnParticle(Particle.BLOCK, loc, 12, 0.3, 0.3, 0.3, 0, data);
        target.getWorld().playSound(loc, data.getSoundGroup().getHitSound(), 1.0f, 0.8f);
    }

    /** Each second: smoke and flames at the roof of each building below half of its hit points, more at fewer hit
     * points, as in AoE2 (#660). Not fire blocks: they spread and burn the design. Tag aoe2mc.burning while it burns. */
    private void burn() {
        for (var e : buildings.entrySet()) {
            Entity t = Bukkit.getEntity(e.getKey());
            Building b = e.getValue();
            if (t == null) {
                continue;
            }
            var score = hp().getScoreFor(t);
            wear(t, b, score.isScoreSet() ? stage(score.getScore(), b.max) : 0);
            boolean burning = score.isScoreSet() && score.getScore() * 2 < b.max;
            if (!burning) {
                t.removeScoreboardTag("aoe2mc.burning");
            } else {
                t.addScoreboardTag("aoe2mc.burning");
            }
            var rnd = ThreadLocalRandom.current();
            int fires = !score.isScoreSet() || score.getScore() * 4 >= b.max * 3 ? 0   // smoke from 75 %, as AoE2
                    : burning ? 1 + (int) (3 * (1 - 2.0 * score.getScore() / b.max)) + (stage(score.getScore(), b.max) / 5) * 2
                    : 1;                                     // 1 fire at half, 4 at 25 %, 6 near 0
            for (int i = 0; i < fires; i++) {
                int x = rnd.nextInt(b.b[0], b.b[3] + 1), z = rnd.nextInt(b.b[2], b.b[5] + 1);
                var top = roof(t, x, z);
                if (top == null) {
                    continue;
                }
                var loc = top.getLocation().add(0.5, 1.1, 0.5);
                if (burning) {
                    t.getWorld().spawnParticle(Particle.FLAME, loc, 6, 0.3, 0.2, 0.3, 0.01);
                }
                t.getWorld().spawnParticle(Particle.LARGE_SMOKE, loc.add(0, 0.5, 0), 4, 0.3, 0.4, 0.3, 0.02);
            }
        }
    }

    /** The original blocks of a worn building (by block key) and its damage stage (#1522). */
    private record Wear(int[] stage, Map<Long, BlockData> blocks) {}

    // Share of the blocks that are gone, and that are worn or gone, per stage (#1650: 6 stages for a smooth change,
    // the owner). Each stage changes only the blocks between its share and the share of the stage before it.
    private static final double[] HOLES = {0, 0.03, 0.06, 0.10, 0.15, 0.24, 0.35};
    private static final double[] WORN = {0, 0.15, 0.30, 0.40, 0.50, 0.60, 0.70};
    private static final int LAST = HOLES.length - 1;                 // almost broken
    private static final double COBWEB = 0.06;                        // of the holes at the last stage: cobwebs, not air

    /** The damage stage of a building with hp of max hit points: 0 above 6/7, then one stage more at each 1/7 below
     *  full, LAST at 1/7 and less (#1522, #1650). */
    static int stage(int hp, int max) {
        return Math.max(0, Math.min(LAST, LAST + 1 - (hp * (LAST + 1) + max - 1) / max));   // the ceiling of hp * 7 / max
    }

    /** A fixed random number in [0, 1) of the block (x, y, z): the same blocks go first at each damage and come back
     *  last at each repair, and the result does not depend on the order of the hits. */
    static double chance(int x, int y, int z) {
        long h = x * 0x9E3779B97F4A7C15L ^ y * 0xC2B2AE3D27D4EB4FL ^ z * 0x165667B19E3779F9L;
        h = (h ^ (h >>> 31)) * 0xBF58476D1CE4E5B9L;
        h = (h ^ (h >>> 29)) * 0x94D049BB133111EBL;
        return ((h ^ (h >>> 32)) >>> 11) * 0x1.0p-53;
    }

    /** The worn form of a block (cracked or mossy bricks, a stripped log, a broken window as air, planks or stairs
     *  broken to a bottom slab of the same material), or null when it has none. */
    static BlockData worn(BlockData data) {
        String s = data.getAsString(), id = s.split("\\[")[0].substring("minecraft:".length());
        String to = switch (id) {
            case "stone_bricks", "deepslate_bricks", "deepslate_tiles", "nether_bricks", "polished_blackstone_bricks"
                    -> "cracked_" + id;
            case "glass", "glass_pane" -> "air";
            default -> id.startsWith("stone_brick_") || id.startsWith("cobblestone") ? "mossy_" + id
                    : (id.endsWith("_log") || id.endsWith("_wood")) && !id.startsWith("stripped_") ? "stripped_" + id
                    : id.endsWith("_stained_glass") || id.endsWith("_stained_glass_pane") ? "air"
                    : id.endsWith("_planks") ? id.replace("_planks", "_slab")
                    : id.endsWith("_stairs") ? id.replace("_stairs", "_slab") : null;
        };
        if (to == null) {
            return null;
        } else if (to.endsWith("_slab")) {                    // a slab has other states than a block or stairs
            try {
                return Bukkit.createBlockData("minecraft:" + to + "[type=bottom]");
            } catch (IllegalArgumentException e) {
                return null;
            }
        }
        try {
            return Bukkit.createBlockData(to.equals("air") ? "minecraft:air" : "minecraft:" + to + s.substring(s.split("\\[")[0].length()));
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    /** Show the damage stage of building t (#1522): at each stage a fixed random share of its blocks above the floor
     *  is worn (worn()) or gone (holes, cobwebs at the last stage), more at each stage, so that almost destroyed looks clearly
     *  other than a little damaged. The blocks go anywhere in the building, not from the top as a construction site
     *  (build.rise). A repair puts the blocks of each stage back. No change to barriers, block entities, fluids and gate bars (#3073): the
     *  units never stand in a block (a hole only removes one), and no item drops (no block updates). */
    private void wear(Entity t, Building b, int stage) {
        Wear w = wear.get(t.getUniqueId());
        if (stage == (w == null ? 0 : w.stage[0])) {
            return;
        }
        var world = t.getWorld();
        if (w == null) {                                      // the first damage: keep the original blocks
            w = new Wear(new int[] {0}, new HashMap<>());
            for (int x = b.b[0]; x <= b.b[3]; x++) {
                for (int y = b.b[1] + 1; y <= b.b[4]; y++) {
                    for (int z = b.b[2]; z <= b.b[5]; z++) {
                        Block block = world.getBlockAt(x, y, z);
                        Material m = block.getType();
                        if (!m.isAir() && m != Material.BARRIER && !block.isLiquid() && !gates.holds(world, x, y, z)
                                && !(block.getState() instanceof org.bukkit.block.TileState)) {
                            w.blocks.put(Block.getBlockKey(x, y, z), block.getBlockData());
                        }
                    }
                }
            }
            wear.put(t.getUniqueId(), w);
        }
        for (var e : w.blocks.entrySet()) {
            int x = Block.getBlockKeyX(e.getKey()), y = Block.getBlockKeyY(e.getKey()), z = Block.getBlockKeyZ(e.getKey());
            double r = chance(x, y, z);
            BlockData to = e.getValue();
            if (r < HOLES[stage]) {
                to = Bukkit.createBlockData(stage == LAST && r < COBWEB ? Material.COBWEB : Material.AIR);
            } else if (r < WORN[stage]) {
                BlockData v = worn(e.getValue());
                to = v != null ? v : to;
            }
            Block block = world.getBlockAt(x, y, z);
            if (!block.getBlockData().equals(to)) {
                block.setBlockData(to, false);
            }
        }
        w.stage[0] = stage;
        if (stage == 0) {                                     // repaired: all blocks are back
            wear.remove(t.getUniqueId());
        }
    }

    /** The name and the hearts of the hit points; visible only when hurt or selected (#661). The first call keeps the
     *  custom name of the converter (the unit name in the player color) as the name. */
    void nameLine(Entity e) {
        if (!(e instanceof LivingEntity le)) {
            return;
        }
        Component name = names.computeIfAbsent(e.getUniqueId(), k -> {
            Component c = le.customName();                    // a world saved by the game program has the hearts
            var parts = c == null ? List.<Component>of() : c.children();
            return parts.size() == 4 && parts.get(3).color() != null
                    && parts.get(3).color().value() == NamedTextColor.DARK_GRAY.value() ? parts.get(0) : c;
        });
        if (name == null) {
            names.remove(e.getUniqueId());
            return;
        }
        Building b = buildings.get(e.getUniqueId());
        AttributeInstance attr = le.getAttribute(Attribute.MAX_HEALTH);
        double hp = b != null ? hp().getScoreFor(e).getScore() : le.getHealth();
        double max = b != null ? b.max : attr != null ? attr.getValue() : hp;
        int full = hp <= 0 ? 0 : Math.max(1, (int) Math.ceil(HEARTS * hp / max - 1e-9));
        Component line = Component.text().append(name).append(Component.text(" "))
                .append(Component.text("❤".repeat(full), NamedTextColor.RED))
                .append(Component.text("❤".repeat(HEARTS - full), NamedTextColor.DARK_GRAY)).build();
        boolean show = hp < max || le.getScoreboardTags().contains("aoe2mc.selected");
        le.customName(line);
        le.setCustomNameVisible(show && b == null);
        if (b != null) {                                      // the client draws no name of an invisible mob (#1811)
            label(e, b, show ? line : null);
        }
    }

    /** Show text over the roof of the building of target e (a text display: not a mob, so no invisibility rule), or
     *  remove it (text null). */
    private void label(Entity e, Building b, Component text) {
        TextDisplay d = labels.get(e.getUniqueId());
        if (d != null && (text == null || !d.isValid())) {
            d.remove();
            labels.remove(e.getUniqueId());
            d = null;
        }
        if (text == null) {
            return;
        }
        if (d == null) {
            Location at = new Location(e.getWorld(), (b.b[0] + b.b[3] + 1) / 2.0, b.b[4] + 2.5, (b.b[2] + b.b[5] + 1) / 2.0);
            d = e.getWorld().spawn(at, TextDisplay.class, t -> {         // over the smoke of the damage (#1522)
                t.setBillboard(Display.Billboard.CENTER);
                t.setTransformation(new Transformation(new Vector3f(), new AxisAngle4f(),
                        new Vector3f(Deaths.SCALE, Deaths.SCALE, Deaths.SCALE), new AxisAngle4f()));
                t.setPersistent(false);
                t.addScoreboardTag(LABEL);
            });
            labels.put(e.getUniqueId(), d);
        }
        d.text(text);
    }

    private boolean ready(Entity unit, Stats a) {
        int now = Bukkit.getCurrentTick(), reload = a.reload;
        for (Ability ab : abilities) {
            reload = ab.reload(unit, reload);                // a Temple Guard (#4468)
        }
        return now - lastHit.getOrDefault(unit.getUniqueId(), -1000) >= reload;
    }

    private void struck(Entity unit) {                       // a melee hit of the unit: its reload starts
        lastHit.put(unit.getUniqueId(), Bukkit.getCurrentTick());
        abilities.forEach(ab -> ab.struck(unit));
    }

    // Each tick: a melee unit next to its target hits when its reload is over. The vanilla melee goal hits each 20
    // ticks and only a living target (a building target is a slime): onHit drops its hits before the reload (#848).
    private void siege() {
        int now = Bukkit.getCurrentTick();
        lastHit.values().removeIf(t -> now - t > 400);
        BRAIN_TARGETS.keySet().removeIf(id -> Bukkit.getEntity(id) == null);
        reaches.keySet().removeIf(id -> Bukkit.getEntity(id) == null);
        for (UUID id : List.copyOf(stats.keySet())) {
            if (Bukkit.getEntity(id) instanceof Mob mob && !stats.get(id).ranged && target(mob) instanceof LivingEntity t
                    && t.isValid() && (buildings.containsKey(t.getUniqueId()) || stats.containsKey(t.getUniqueId()))
                    && !chase(mob, t, now)
                    && ready(mob, stats.get(id)) && mob.getBoundingBox().expand(reach(mob), 0, reach(mob)).overlaps(t.getBoundingBox())) {
                if (mob.getAttribute(Attribute.ATTACK_DAMAGE) == null) {
                    // Mob#attack throws on a kind without it (a chicken, a camel), and the throw stopped this loop for
                    // the units after it (#1968). onHit takes the AoE2 damage, so the value does not matter.
                    mob.registerAttribute(Attribute.ATTACK_DAMAGE);
                }
                mob.swingMainHand();
                mob.attack(t);
            }
        }
    }

    // A hoglin (a bear, #3624) has a brain: Mob#getTarget reads its attack memory, which the API cannot set, so it
    // gives null after Mob#setTarget. The plugin keeps the target of a hoglin here; the other mobs use their own.
    private static final Map<UUID, UUID> BRAIN_TARGETS = new HashMap<>();

    static LivingEntity target(Mob mob) {
        if (!(mob instanceof Hoglin)) {
            return mob.getTarget();
        }
        UUID id = BRAIN_TARGETS.get(mob.getUniqueId());
        return id != null && Bukkit.getEntity(id) instanceof LivingEntity t ? t : null;
    }

    private static void setTarget(Mob mob, LivingEntity t) {
        mob.setTarget(t);
        if (t == null) {
            BRAIN_TARGETS.remove(mob.getUniqueId());
        } else if (mob instanceof Hoglin) {
            BRAIN_TARGETS.put(mob.getUniqueId(), t.getUniqueId());
        }
    }

    // A hoglin does not walk to that target with its brain either: out of reach, it walks there with the Minecraft
    // path finding, a new path each 10 ticks. True while it walks.
    private boolean chase(Mob mob, LivingEntity t, int now) {
        if (!(mob instanceof Hoglin) || mob.getBoundingBox().expand(reach(mob), 0, reach(mob)).overlaps(t.getBoundingBox())) {
            return false;
        }
        if (now % 10 == 0 || !mob.getPathfinder().hasPath()) {
            mob.getPathfinder().moveTo(t);
        }
        return true;
    }

    // The cart of a War Wagon (#2746) is an item display that rides its horse (units.cart). A passenger keeps its own
    // rotation (Entity#positionRider moves it, but turns only a living passenger): the cart turns with the body of the
    // horse here, so it stays behind the horse after a turn. No vanilla feature does it.
    private void carts() {
        for (UUID id : List.copyOf(stats.keySet())) {
            if (Bukkit.getEntity(id) instanceof AbstractHorse h) {
                for (Entity p : h.getPassengers()) {
                    if (p instanceof ItemDisplay d && d.getYaw() != h.getBodyYaw()) {
                        d.setRotation(h.getBodyYaw(), 0);
                    }
                }
            }
        }
    }

    // aoe charge and aoe detonate (#2165): the values go to the crew of a ship or a minecart, which has the AoE2 values
    // and dies (#1386, #3013, #4367).
    private boolean charges(CommandSender sender, String selector, Map<UUID, Charge> to, String ticks, String attack,
                            String shots, String blast, String bonus, boolean foes) {
        Charge c;
        try {
            c = new Charge(Integer.parseInt(ticks), new Stats(Integer.parseInt(attack), 0, 0, false, false, Set.of(),
                    bonus(bonus), 20), Integer.parseInt(shots), Double.parseDouble(blast));
        } catch (RuntimeException e) {                     // a bad number or a bonus without ":"
            sender.sendMessage("Bad value: " + e.getMessage());
            return true;
        }
        int n = 0;
        for (Entity e : select(sender, selector)) {
            if (crew(e) instanceof LivingEntity le) {
                to.put(le.getUniqueId(), c);
                if (to == detonations && foes) {
                    spare.add(le.getUniqueId());
                } else if (to == detonations) {
                    spare.remove(le.getUniqueId());
                }
                n++;
            }
        }
        sender.sendMessage((to == charges ? "Charge: " : "Detonate: ") + n + " units");
        return true;
    }

    private static Map<String, Integer> bonus(String text) {
        var m = new HashMap<String, Integer>();
        if (!text.equals("-")) {
            for (String kv : text.split(",")) {
                String[] p = kv.split(":");
                m.put(p[0], Integer.parseInt(p[1]));
            }
        }
        return m;
    }

    /** A unit that walks with a brain, not with goals: without NoAI it strolls away (#438, #1968, #3541). */
    private boolean brained(Mob mob) {
        return mob instanceof Villager || mob instanceof Camel || mob.getScoreboardTags().contains(CARRIER);
    }

    private void follow() {
        orders.entrySet().removeIf(e -> {
            Entity ent = Bukkit.getEntity(e.getKey());
            if (!(ent instanceof Mob mob) || !mob.isValid()) {
                return true;
            }
            Order o = e.getValue();
            if (mob.getLocation().distanceSquared(o.goal) < 1.5 * 1.5) {
                // a brain has no goals to drop: it strolls away (#438, #1968); a minecart pushes its carrier on (#836)
                if (brained(mob)) {
                    mob.getPathfinder().stopPathfinding();   // without AI it keeps its path: Gates.through kept a gate open (#1928)
                    mob.setAI(false);               // so it stands still until the next order
                } else if (center(mob) >= 1) {      // steer() skips path points: Minecraft walks back to them (#1078)
                    mob.getPathfinder().stopPathfinding();
                } else if (elsewhere(mob, o.goal) || behind(mob, o.goal)) {
                    mob.getPathfinder().stopPathfinding();
                    mob.setVelocity(new Vector(0, mob.getVelocity().getY(), 0));   // a fast unit slid on (#1292)
                }
                return true;                                          // arrived
            }
            var pf = mob.getPathfinder();
            var path = pf.getCurrentPath();
            if (path == null || path.getFinalPoint() == null
                    || path.getFinalPoint().distanceSquared(o.goal) > 1.5 * 1.5) {
                double c = center(mob);
                if (path != null && path.getFinalPoint() != null
                        && path.getFinalPoint().clone().add(c, 0, c).distanceSquared(mob.getLocation()) <= 1.5 * 1.5) {
                    // at the end of a part of the way: a new search from here. moveTo gives the old part again (a
                    // not done path to the same target), so the order ended as "no path" 10 to 20 blocks before
                    // a rally point that a new search reaches (de-64.3, #2303).
                    pf.stopPathfinding();
                }
                boolean found = pf.moveTo(o.goal, o.speed);
                Location end = pf.getCurrentPath() == null ? null : pf.getCurrentPath().getFinalPoint();
                // a part of a path that ends at the mob leads nowhere: a builder of a dock stood still with its order
                // for a minute (#889). Drop such an order after 1 s.
                boolean stays = found && end != null && end.clone().add(c, 0, c).distanceSquared(mob.getLocation()) <= 1.5 * 1.5;
                if (found && !stays || (o.fails += stays ? 5 : 1) < 50) {
                    return false;
                }
                pf.stopPathfinding();                   // it stays here: the old part led it away (#2303)
                if (brained(mob)) {                     // no path for 5 s: drop the order, and stop the brain (#811, #3541)
                    mob.setAI(false);
                }
                getLogger().info("aoe2mc: no path " + mob.getUniqueId() + " " + o.goal.getX() + " " + o.goal.getY()
                        + " " + o.goal.getZ());
                return true;
            }
            if (passed(mob, path)) {
                pf.stopPathfinding();                   // else moveTo keeps the path: same target (createPath)
                pf.moveTo(o.goal, o.speed);
            }
            return false;
        });
    }

    // A land unit keeps out of water deeper than 1 block (AoE2: only ships go there), but walks through the 1-block
    // shallows (#1198, #1669). PathType.WATER is the type of both, and Paper has no malus setter: the server has the
    // Mojang names at run time (Mob#setPathfindingMalus). A malus of -1 blocks the water, so only for an order whose
    // path goes through deep water: then the unit walks around the lake, or stops at the shore. The crew of a ship sails.
    private void dry(Mob mob, Location goal) {
        Float old = wet.remove(mob.getUniqueId());
        if (old != null) {
            malus(mob, old);                                    // the water of the last order is open again
        }
        if (mob.getVehicle() instanceof Boat || mob.isInWater()) {
            return;                                             // a unit in the water swims out (#1208)
        }
        // findPath sets the target of the navigation to goal: with the last path still on, moveTo then takes that old
        // path again (a not done path to the same target), and the unit keeps its last order (#1713)
        mob.getPathfinder().stopPathfinding();
        var path = mob.getPathfinder().findPath(goal);
        if (path != null && path.getPoints().stream().anyMatch(AoePlugin::deep) && (old = malus(mob, -1f)) != null) {
            wet.put(mob.getUniqueId(), old);
        }
    }

    // Water above or under the water of a path point: deeper than 1 block. A unit that sinks walks on the floor
    // (water above it), a horse swims at the top (water under it).
    private static boolean deep(Location p) {
        Block b = p.getBlock();
        return b.getType() == Material.WATER && (b.getRelative(0, 1, 0).getType() == Material.WATER
                || b.getRelative(0, -1, 0).getType() == Material.WATER);
    }

    // Set the path malus of PathType.WATER of the mob. Returns the malus before, or null when the server has no such
    // method (another mapping): then the unit walks as before.
    private Float malus(Mob mob, float value) {
        try {
            Object handle = mob.getClass().getMethod("getHandle").invoke(mob);
            Class<?> type = Class.forName("net.minecraft.world.level.pathfinder.PathType");
            Object water = type.getField("WATER").get(null);
            float old = (float) handle.getClass().getMethod("getPathfindingMalus", type).invoke(handle, water);
            handle.getClass().getMethod("setPathfindingMalus", type, float.class).invoke(handle, water, value);
            return old;
        } catch (ReflectiveOperationException | RuntimeException e) {
            if (!noMalus) {
                getLogger().warning("aoe2mc: no path malus: " + e);
                noMalus = true;
            }
            return null;
        }
    }

    // The path ends on another block than the goal (the goal block has no place to stand, so the path ends at the
    // nearest free block): the rest of the path only passes the goal, a move without an order (#1292: an eagle scout
    // of the replay walked 2 blocks past its replay position).
    private static boolean elsewhere(Mob mob, Location goal) {
        var path = mob.getPathfinder().getCurrentPath();
        Location end = path == null ? null : path.getFinalPoint();
        return end == null || end.getBlockX() != goal.getBlockX() || end.getBlockZ() != goal.getBlockZ();
    }

    // The next point of the path is not at the goal: steer() and glide() took the mob past points that Minecraft did
    // not count (passed() looks only on the ground), and with no order it walks back to them. A spearman of de-64.3
    // arrived and then walked 25 blocks back up the hill that it came down (#2303: 22 strays in 35 minutes).
    private static boolean behind(Mob mob, Location goal) {
        var path = mob.getPathfinder().getCurrentPath();
        if (path == null || path.getNextPointIndex() >= path.getPoints().size()) {
            return false;
        }
        double c = center(mob);
        return path.getPoints().get(path.getNextPointIndex()).clone().add(c, 0, c).distanceSquared(goal) > 1.5 * 1.5;
    }

    // The mob is on the ground beyond the next point of its path. Down a slope it lands past the point after each
    // drop of one block, and Minecraft walks back to it: a scout walked at 5.7 of 17.6 blocks per second (#888).
    // A new path starts where the mob is.
    private static boolean passed(Mob mob, Pathfinder.PathResult path) {
        int i = path.getNextPointIndex();
        List<Location> points = path.getPoints();
        if (!mob.isOnGround() || i <= 0 || i + 1 >= points.size()) {
            return false;
        }
        Location a = points.get(i), b = points.get(i + 1), m = mob.getLocation();
        double c = center(mob);
        return (a.getX() + c - m.getX()) * (b.getX() - a.getX()) + (a.getZ() + c - m.getZ()) * (b.getZ() - a.getZ()) < 0;
    }

    // The mob walks to this offset of the corner of a path point: 1 for a horse (2 x 2 blocks), else 0.5 (vanilla
    // Path#getEntityPosAtNode)
    private static double center(Mob mob) {
        return (int) (mob.getWidth() + 1) * 0.5;
    }

    // Down a slope a mob is in the air most of the time, and a mob has almost no control in the air (0.02 blocks per
    // tick, drag 0.91): a fast unit flew at about 5 blocks per second for each movement_speed (#888). On the way down
    // to the first point of its path that is still ahead, it keeps its walk speed (game/ai.py: WALK x attribute^2
    // blocks per second), and it falls along the path, not above it (gravity is slower than a slope of 1:1, #1078).
    // The path finder plans no drop larger than the safe fall distance, so the glide along it does not hurt either:
    // the fall distance and the height above the point are together at most that. It aims at a point at least one
    // tick of the glide ahead: a horse aimed at a point closer than that, passed it in one tick and turned back the
    // next tick, at half its speed (#889).
    private static void glide(Mob mob, Pathfinder.PathResult path, double speed) {
        Vector v = mob.getVelocity();
        AttributeInstance attr = mob.getAttribute(Attribute.MOVEMENT_SPEED);
        List<Location> points = path.getPoints();
        if (mob.isOnGround() || mob.isInWater() || attr == null || points.isEmpty()) {
            return;
        }
        Location m = mob.getLocation(), f = points.get(points.size() - 1), n = f;
        double c = center(mob), step = Math.max(0.05, WALK * attr.getValue() * attr.getValue() * speed / 20);
        int i0 = Math.max(path.getNextPointIndex(), 0), k = ahead(points, i0, m.getX() - c, m.getZ() - c);
        k = c < 1 && !slope(points, i0, k, m) ? -1 : k;
        if (k >= 0 && Math.hypot(points.get(k).getX() + c - m.getX(), points.get(k).getZ() + c - m.getZ()) >= step) {
            n = points.get(k);                          // no zigzag in the air either (#1022)
        } else {
            for (int i = Math.max(path.getNextPointIndex(), 1); i < points.size(); i++) {
                Location a = points.get(i - 1), p = points.get(i);
                double dx = p.getX() + c - m.getX(), dz = p.getZ() + c - m.getZ();
                if (dx * (p.getX() - a.getX()) + dz * (p.getZ() - a.getZ()) > 0 && Math.hypot(dx, dz) >= step) {
                    n = p;                              // the first point that is still ahead
                    break;
                }
            }
        }
        AttributeInstance safe = mob.getAttribute(Attribute.SAFE_FALL_DISTANCE);
        double most = (safe == null ? 3 : safe.getValue()) - Math.max(0, m.getY() - n.getY());   // with the rest of the fall
        mob.setFallDistance((float) Math.max(0, Math.min(mob.getFallDistance(), most)));
        double dx = n.getX() + c - m.getX(), dz = n.getZ() + c - m.getZ(), d = Math.hypot(dx, dz);
        if (v.getY() >= 0 || n.getY() >= m.getY() || d < 0.05) {
            return;
        }
        // glide() runs each tick, so only a landing in this tick limits the speed: then the mob slides on the ground
        // (1 / (1 - GROUND) blocks for each block per tick). A limit for a stop in the air (11 blocks for each block per
        // tick) slowed a horse in the last 6 blocks of a slope to half its speed (#1078).
        boolean lands = (v.getY() - 0.08) * 0.98 <= f.getY() - m.getY();
        double r = Math.hypot(f.getX() + c - m.getX(), f.getZ() + c - m.getZ()), stop = lands ? r * (1 - GROUND) : r;
        double w = Math.min(stop, Math.min(step, d)), h = Math.hypot(v.getX(), v.getZ());
        double vy = Math.min(v.getY(), (n.getY() - m.getY()) * w / d);   // down along the path, not above it
        if (w > h || h > stop || vy < v.getY()) {      // faster, or slower so that it stops at the end of the path
            mob.setVelocity(new Vector(dx / d * w, vy, dz / d * w));
        }
    }

    private void steer() {
        for (var e : orders.entrySet()) {
            if (Bukkit.getEntity(e.getKey()) instanceof Mob mob && mob.isValid()) {
                Order o = e.getValue();
                if (mob instanceof AbstractHorse h && (h.isEatingGrass() || h.isRearing())) {
                    h.setEatingGrass(false);            // an eating horse has no AI step and no path follow (#1359)
                    h.setRearing(false);
                }
                var pf = mob.getPathfinder();
                if (pf.getCurrentPath() == null && Bukkit.getCurrentTick() - o.start < 4) {
                    pf.moveTo(o.goal, o.speed);         // a unit without AI finds its path a tick later: try each tick
                }
                var path = pf.getCurrentPath();
                if (path != null) {
                    steer(mob, path, o);
                    glide(mob, path, o.speed);
                }
                climb(mob, o.goal);                    // also when its path ends in the water
            }
        }
    }

    // The path of a mob goes up and down a slope in L steps: a fast horse swung from side to side, stepped up onto the
    // corner of a block and fell back (#1022), an eagle scout walked up at 56 % of its speed (#851). On the ground it
    // aims at the last path point up to LOOK blocks ahead of the point next to it, whose points between are at most OFF
    // blocks off the line. Each tick the input of the mob (Minecraft MoveControl) pushes toward its next point n with
    // step x (1 - GROUND): the velocity takes that push away again. The path follow can pass n in the same tick, after
    // steer(), and the input then pushes toward the next point: a horse walked 27 % faster to the north-west (#1344).
    // So after the first tick it takes away the real push of the last tick (the move less the velocity, at most the
    // push): its errors cancel from tick to tick, and the mean speed is the walk speed.
    private static void steer(Mob mob, Pathfinder.PathResult path, Order o) {
        double speed = o.speed;
        AttributeInstance attr = mob.getAttribute(Attribute.MOVEMENT_SPEED);
        List<Location> points = path.getPoints();
        int i = path.getNextPointIndex();
        if (!mob.isOnGround() || mob.isInWater() || attr == null || i < 0 || i + 1 >= points.size()) {
            return;
        }
        Location m = mob.getLocation(), n = points.get(i);
        double c = center(mob), mx = m.getX() - c, mz = m.getZ() - c;      // the mob as a corner of a path point
        int k = ahead(points, i, mx, mz);
        if (c < 1 && !slope(points, i, k, m)) {
            return;
        }
        Location p = points.get(k);
        double step = WALK * attr.getValue() * attr.getValue() * speed / 20, push = step * (1 - GROUND);
        double dx = p.getX() - mx, dz = p.getZ() - mz, d = Math.hypot(dx, dz);
        double nx = n.getX() - mx, nz = n.getZ() - mz, e = Math.hypot(nx, nz);
        if (e > 0.01) {
            nx *= push / e;
            nz *= push / e;
        }
        if (o.at == Bukkit.getCurrentTick() - 1) {     // the real push of the last tick: the move less the velocity (#1344)
            double ax = m.getX() - o.px - o.vx, az = m.getZ() - o.pz - o.vz, a = Math.hypot(ax, az);
            nx = a > push ? ax / a * push : ax;
            nz = a > push ? az / a * push : az;
        }
        if (d < 0.05) {
            return;
        }
        double w = Math.min(step, d), vx = dx / d * w - nx, vz = dz / d * w - nz;
        mob.setVelocity(new Vector(vx, mob.getVelocity().getY(), vz));
        o.px = m.getX();
        o.pz = m.getZ();
        o.vx = vx;
        o.vz = vz;
        o.at = Bukkit.getCurrentTick();
    }

    // A swimming mob floats about 1.5 blocks under a bank of one block above the water, the shore of the maps: Minecraft
    // lifts it out only when 0.6 blocks up are free (LivingEntity#travel in water), and its path ends in the water
    // (#1208: a replay villager stayed in the water and lost its order). In front of such a bank on the way to its goal,
    // it jumps out, as a player does.
    private static void climb(Mob mob, Location goal) {
        Location m = mob.getLocation();
        double dx = goal.getX() - m.getX(), dz = goal.getZ() - m.getZ(), d = Math.hypot(dx, dz);
        Block under = m.getBlock();
        boolean wet = mob.isInWater() || under.getRelative(0, -1, 0).isLiquid() || under.getRelative(0, -2, 0).isLiquid();
        if (!wet || d < 1.5) {
            return;
        }
        double ahead = mob.getWidth() / 2 + 0.7;             // the next block, also 0.8 blocks from the bank
        Block front = m.clone().add(dx / d * ahead, 0, dz / d * ahead).getBlock();
        Block top = null;
        for (int up = -1; up <= 2 && top == null; up++) {      // the top of the bank: a solid block, 2 free above it
            Block b = front.getRelative(0, up, 0);
            if (!b.isPassable() && b.getRelative(0, 1, 0).isPassable() && b.getRelative(0, 2, 0).isPassable()
                    && !b.getRelative(0, 1, 0).isLiquid()) {
                top = b;
            }
        }
        if (top == null || top.getY() + 1 - m.getY() > 1.6) {
            return;
        }
        Vector v = mob.getVelocity();
        if (m.getY() >= top.getY() + 0.9) {                       // above the bank: over the edge
            mob.setVelocity(new Vector(dx / d * CLIMB[1], v.getY(), dz / d * CLIMB[1]));   // it falls: no hover
        } else if (mob.isInWater() && v.getY() <= 0.1) {
            mob.setVelocity(new Vector(dx / d * CLIMB[1], CLIMB[0], dz / d * CLIMB[1]));
        }
    }

    // A path point from i to k is not at the height of the mob. A mob of less than 1 block steers only there: on flat
    // ground its path has no L steps that slow it, and a line past the corner of a building held villagers in place
    // (#851).
    private static boolean slope(List<Location> points, int i, int k, Location m) {
        for (int j = Math.max(i, 0); j <= k && j < points.size(); j++) {
            if (points.get(j).getBlockY() != m.getBlockY()) {
                return true;
            }
        }
        return false;
    }

    // The index of the last path point up to LOOK blocks ahead of the point next to the mob (at the corner mx, mz)
    // whose points between are at most OFF blocks off the line from the mob, at least the one after it.
    private static int ahead(List<Location> points, int i, double mx, double mz) {
        int s = i;
        for (int j = i + 1; j < points.size() - 1; j++) {   // Minecraft can count a steered mob many points back
            Location p = points.get(j), q = points.get(s);
            if (Math.hypot(p.getX() - mx, p.getZ() - mz) < Math.hypot(q.getX() - mx, q.getZ() - mz)) {
                s = j;                                  // the point next to the mob
            }
        }
        int k = Math.min(s + 1, points.size() - 1);
        for (int j = s + 2; j < points.size(); j++) {
            Location p = points.get(j);
            double dx = p.getX() - mx, dz = p.getZ() - mz, d = Math.hypot(dx, dz);
            boolean near = d <= LOOK;
            for (int q = s + 1; q < j && near; q++) {
                Location o = points.get(q);
                near = Math.abs((o.getX() - mx) * dz - (o.getZ() - mz) * dx) / d <= OFF;
            }
            if (!near) {
                break;
            }
            k = j;
        }
        return k;
    }

    // The path search reaches only about the follow range: raise it for a goal at this location. A rider searches
    // with the navigation of its horse (#710): raise it for the horse too.
    private static void reach(Mob mob, Location goal) {
        AttributeInstance range = mob.getAttribute(Attribute.FOLLOW_RANGE);
        if (range != null) {
            double need = Math.min(128, 2 * mob.getLocation().distance(goal) + 32);
            range.setBaseValue(Math.max(range.getBaseValue(), need));
        }
        if (mob.getVehicle() instanceof Mob horse) {
            reach(horse, goal);
        }
    }

    // The rider of a mounted unit, or null (#710).
    private static Mob rider(Entity e) {
        return e instanceof Mob && e.getPassengers().size() > 0 && e.getPassengers().get(0) instanceof Mob r ? r : null;
    }

    /** The mob that carries a siege unit (#836). A minecart is no mob, and Minecraft has no path finding for it: so
     *  an invisible small pig carries it, and the orders go to the pig. The first order makes it. */
    static Mob carrier(Minecart cart, boolean make) {
        if (cart.getVehicle() instanceof Mob m && m.getScoreboardTags().contains(CARRIER)) {
            return m;
        }
        if (!make || cart.getVehicle() != null) {
            return null;
        }
        Pig pig = cart.getWorld().spawn(cart.getLocation(), Pig.class, p -> {
            p.setInvisible(true);
            p.setSilent(true);
            p.setInvulnerable(true);           // the hits go to the crew (aoe stats), not to the carrier
            p.setPersistent(true);
            p.addScoreboardTag(CARRIER);
            AttributeInstance scale = p.getAttribute(Attribute.SCALE);
            if (scale != null) {
                scale.setBaseValue(CARRIER_SCALE);  // the minecart rides near the ground
            }
            AttributeInstance step = p.getAttribute(Attribute.STEP_HEIGHT);
            if (step != null) {
                step.setBaseValue(STEP);            // up one block, as the other units
            }
        });
        pig.addPassenger(cart);
        return pig;
    }

    /** The crew of a ship (a boat, units.py): its first passenger, a mob with the AoE2 values (#1386). Else e. */
    static Entity sailors(Entity e) {
        return e instanceof Boat && !e.getPassengers().isEmpty() && e.getPassengers().get(0) instanceof LivingEntity c
                ? c : e;
    }

    /** The entity with the AoE2 values of a part of a unit: the crew of a boat or of a minecart, else e (#3013). */
    static Entity crew(Entity e) {
        return e instanceof Minecart && !e.getPassengers().isEmpty() ? e.getPassengers().get(0) : sailors(e);
    }

    /** The entity that walks for e: the carrier of a siege unit, else e. */
    private static Entity walker(Entity e) {
        return e instanceof Minecart cart && carrier(cart, false) != null ? carrier(cart, false) : e;
    }

    private Mob unit(Entity e) {
        if (e instanceof Boat && sailors(e) instanceof Mob c) {
            return unit(c);                              // a ship: the crew takes the orders, fleet.py sails (#1386)
        }
        if (e instanceof Minecart cart) {
            Mob c = carrier(cart, true);
            return c == null ? null : unit(c);
        }
        if (!(e instanceof Mob mob)) {
            return null;
        }
        if (!mob.hasAI()) {
            mob.setAI(true);
            // a mob without AI does not move, but the pushes of the units on its place add to its velocity: 8 villagers
            // that stood on one cell for 12 s flew 20 to 40 blocks at their next order (#1168)
            mob.setVelocity(new Vector(0, mob.getVelocity().getY(), 0));
        }
        tame(mob);                  // each order: tame() only after setAI() missed the goals of some units (#436)
        AttributeInstance step = mob.getAttribute(Attribute.STEP_HEIGHT);
        if (step != null && step.getBaseValue() < STEP) {
            step.setBaseValue(STEP);                                   // no jump on a step of one block (#829)
        }
        AttributeInstance swim = mob.getAttribute(Attribute.WATER_MOVEMENT_EFFICIENCY);
        if (swim != null) {         // as Depth Strider III: a path through water at about the walk speed (#1208)
            swim.setBaseValue(1);
        }
        Range r = ranges.get(mob.getUniqueId());
        if (r == null && mob.getScoreboardTags().contains(CARRIER) && !mob.getPassengers().isEmpty()) {
            r = ranges.get(mob.getPassengers().get(0).getUniqueId());      // the range of its siege unit (#1050)
        }
        var goals = Bukkit.getMobGoals();
        if (r != null && (mob instanceof RangedEntity || r.siege)) {
            for (var g : goals.getAllGoals(mob)) {
                String k = g.getKey().getNamespacedKey().getKey();
                // the creeper of a demolition ship and the petard (#2192): no vanilla explosion, the AoE2 blast hits
                if (SHOTS.contains(k) || r.siege && (k.equals("melee_attack") || k.equals("swell"))) {
                    goals.removeGoal(mob, g.getKey());
                }
            }
            if (!goals.hasGoal(mob, rangeKey)) {
                goals.addGoal(mob, 4, new RangeGoal(mob, r));          // the priority of the vanilla bow goal
            }
        } else if (r == null && rider(mob) == null && mob.getVehicle() == null && !(mob instanceof Villager)
                && stats.get(mob.getUniqueId()) instanceof Stats s && !s.ranged()
                && s.attack() > 0 && !goals.hasGoal(mob, chaseKey) && goals.getAllGoals(mob).stream()
                        .noneMatch(g -> MELEES.contains(g.getKey().getNamespacedKey().getKey()))) {
            goals.addGoal(mob, 2, new ChaseGoal(mob));                 // the priority of the vanilla melee goal
        }
        return mob;
    }

    // The goals that a unit keeps: swim, and attack the target of an order. The keys of the other goals (26.3):
    // nearest_attackable and hurt_by choose targets, random_stroll, look_at_player, panic, tempt, breed, flee_sun ...
    private static final Set<String> KEEP = Set.of("float", "melee_attack", "zombie_attack", "ocelot_attack",
            "skeleton_melee", "spear_use", "ranged_attack", "ranged_bow_attack", "ranged_crossbow_attack", "aoe_range",
            "aoe_chase");

    static boolean keep(String goal) {
        return KEEP.contains(goal);
    }

    private static void tame(Mob mob) {
        var goals = Bukkit.getMobGoals();
        var drop = new java.util.HashSet<com.destroystokyo.paper.entity.ai.GoalKey<Mob>>();
        for (var g : goals.getAllGoals(mob)) {                // by key: the goal objects are new wrappers each time
            if (!keep(g.getKey().getNamespacedKey().getKey())) {
                drop.add(g.getKey());
            }
        }
        for (var key : drop) {
            goals.removeGoal(mob, key);
        }
        mob.setRemoveWhenFarAway(false);
        mob.setPersistent(true);
        AttributeInstance fire = mob.getAttribute(Attribute.BURNING_TIME);   // Zombie#setShouldBurnInDay does
        if (fire != null) {                                                   // nothing in 26.3: no fire, no sun burn
            fire.setBaseValue(0);
        }
    }

    private static boolean afloat(Entity e) {                // the crew of a ship on the water (#1658)
        return e.getVehicle() instanceof Boat boat && boat.isInWater();
    }

    private boolean ranged(Mob mob) {
        Stats s = stats.get(mob.getUniqueId());
        return s != null && s.ranged();
    }

    static boolean sameTeam(Entity a, Entity b) {
        return allied(side(a), side(b));
    }

    // team -> the teams that it is neutral to (aoe neutral, #1645): no automatic attack on their units, as in AoE2
    private static final Map<String, Set<String>> NEUTRAL = new HashMap<>();

    /** True when the units of a do not attack b by themselves: the same side, an ally, a neutral stance, or the tag
     *  NO_TARGET on b. */
    private static boolean calm(Entity a, Entity b) {
        String s = side(b);         // no side (the crew of a siege unit, #1820): Set.of().contains(null) throws
        if (side(a) == null && s == null) {     // a predator of Gaia attacks no animal and no Gaia unit (#3397)
            return true;
        }
        return sameTeam(a, b) || s != null && NEUTRAL.getOrDefault(side(a), Set.of()).contains(s)
                || b.getScoreboardTags().contains(NO_TARGET);       // "Disable Unit Targeting" of a trigger (#2826)
    }

    // team -> the elevation factors up, low, high (aoe elevation, #2307); the blocks of one level, 0: no rule
    private static final Map<String, double[]> ELEVATION = new HashMap<>();
    private static final double[] ELEVATION_BASE = {1.25, 0.75, 1.0};
    private static int elevationStep = 0;

    /** The factor of the damage of a hit from attacker `from` (a shot: its shooter) on `to`: the same rule as
     *  game/combat.py elevation. A unit on a horse, boat or carrier stands where its vehicle stands. */
    static double elevation(Entity from, Entity to) {
        if (from instanceof Projectile p && p.getShooter() instanceof Entity shooter) {
            from = shooter;
        }
        Entity a = from.getVehicle() != null ? from.getVehicle() : from, t = to.getVehicle() != null ? to.getVehicle() : to;
        int dy = a.getLocation().getBlockY() - t.getLocation().getBlockY();
        if (elevationStep <= 0 || Math.abs(dy) < elevationStep) {
            return 1.0;
        }
        double[] fa = ELEVATION.getOrDefault(side(from) != null ? side(from) : side(a), ELEVATION_BASE);
        double[] ft = ELEVATION.getOrDefault(side(to) != null ? side(to) : side(t), ELEVATION_BASE);
        return dy > 0 ? fa[0] * ft[2] : ft[1];
    }

    // team -> the first team of its alliance (aoe allies, #1315): allied players are one side, as in AoE2
    private static final Map<String, String> ALLIES = new HashMap<>();

    /** True when the sides a and b (side()) are the same player or allies. No side: no ally of anyone. */
    // A shot of an own or allied unit (#2418): the crew of a siege unit or a ship can have no team, its vehicle has it.
    private static boolean friendlyFire(Entity from, Entity victim) {
        String s = side(from) == null && from.getVehicle() != null ? side(from.getVehicle()) : side(from);
        return allied(s, side(victim));
    }

    static boolean allied(String a, String b) {
        return a != null && b != null && ALLIES.getOrDefault(a, a).equals(ALLIES.getOrDefault(b, b));
    }

    // The team name, else the player tag aoe2mc.pN: the pulse of the datapack puts a unit in its team only when its
    // chunk is loaded, and two units without a team are not enemies (#986: idle soldiers killed their neighbours).
    // Gaia (the tag aoe2mc.p0 of the triggers, #2916) has no side.
    static String side(Entity e) {
        Team t = Bukkit.getScoreboardManager().getMainScoreboard().getEntityTeam(e);
        if (t != null) {
            return t.getName();
        }
        for (String tag : e.getScoreboardTags()) {
            if (tag.matches("aoe2mc\\.p[1-9]\\d*")) {
                return tag.substring(7);
            }
        }
        return null;
    }

    static List<Entity> select(CommandSender sender, String selector) {
        try {
            return Bukkit.selectEntities(sender, selector);
        } catch (IllegalArgumentException e) {
            return List.of();
        }
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (command.getName().equals("aoego")) {                       // a click on an attack alert (#1816)
            return alerts.go(sender, args);
        }
        if (args.length >= 2 && args[0].startsWith("ghost")) {          // the ghost of a building (#794)
            return ghost.command(sender, args, players(sender, args[1]));
        }
        for (Ability ab : abilities) {                                  // a unit ability (#4589)
            if (args.length >= 1 && args[0].equals(ab.name()) && ab.command(this, sender, args)) {
                return true;
            }
        }
        if ((args.length == 3 || args.length == 5) && args[0].equals("accuracy")) {   // a trebuchet misses units (#2479)
            double part;
            double[] miss;
            try {
                part = Double.parseDouble(args[2]);
                miss = args.length == 5 ? new double[] {Double.parseDouble(args[3]), Double.parseDouble(args[4])} : null;
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                for (Entity t : concat(crew(e), e.getPassengers())) {   // the crew of a siege unit has its stats (#836),
                    accuracy.put(t.getUniqueId(), part);                // the rider of a horse shoots (#732)
                    if (miss != null) {
                        misses.put(t.getUniqueId(), miss);
                    } else {
                        misses.remove(t.getUniqueId());
                    }
                }
                n++;
            }
            sender.sendMessage("Accuracy: " + n + " units");
            return true;
        }
        if ((args.length == 4 || args.length == 5) && args[0].equals("dodge")) {   // a Shrivamsha Rider (#4399)
            int shots, ticks;
            boolean melee = args.length == 5 && args[4].equals("1");      // an Iron Pagoda (#4465)
            try {
                shots = Integer.parseInt(args[2]);
                ticks = Integer.parseInt(args[3]);
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                for (Entity t : new Entity[] {crew(e), e.getVehicle()}) {   // the rider and its horse (#732)
                    if (t != null) {
                        dodges.put(t.getUniqueId(), new Dodge(shots, ticks, melee));
                    }
                }
                n++;
            }
            sender.sendMessage("Dodge: " + n + " units");
            return true;
        }
        if (args.length == 6 && args[0].equals("pack")) {             // a Monaspa: attack near its pack (#4469)
            int per, max;
            double blocks;
            try {
                per = Integer.parseInt(args[2]);
                blocks = Double.parseDouble(args[3]);
                max = Integer.parseInt(args[4]);
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            Pack pk = new Pack(Math.max(1, per), blocks, max, Set.of(args[5].split(",")));
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                for (Entity t : new Entity[] {crew(e), e.getVehicle(), e}) {   // the rider and its horse (#732)
                    if (t != null) {
                        packs.put(t.getUniqueId(), pk);
                    }
                }
                n++;
            }
            sender.sendMessage("Pack: " + n + " units");
            return true;
        }
        if (args.length == 5 && args[0].equals("speedcharge")) {      // a Samurai: faster near its target (#4545)
            double[] c;
            try {
                c = new double[] {Double.parseDouble(args[2]), Double.parseDouble(args[3]), Double.parseDouble(args[4])};
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                Entity u = rider(e) instanceof Mob r ? r : e;      // the rider of a mounted unit has the target (#710)
                speedCharges.put(u.getUniqueId(), c);
                n++;
            }
            sender.sendMessage("Speed charge: " + n + " units");
            return true;
        }
        if (args.length == 3 && args[0].equals("sunder")) {           // an Obuch: armor less per hit (#4466)
            int armor;
            try {
                armor = Integer.parseInt(args[2]);
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                for (Entity t : new Entity[] {crew(e), e.getVehicle(), e}) {   // the rider and its horse (#732)
                    if (t != null) {
                        sunders.put(t.getUniqueId(), armor);
                    }
                }
                n++;
            }
            sender.sendMessage("Sunder: " + n + " units");
            return true;
        }
        if ((args.length == 6 || args.length == 7 && args[6].equals("buildings")) && args[0].equals("afterblast")) {
            AfterBlast b;                                              // Thunderclap Bombs (#4369)
            try {
                b = new AfterBlast(new Charge(Math.max(1, Integer.parseInt(args[2])), new Stats(Integer.parseInt(args[3]),
                        0, 0, false, false, Set.of(), Map.of(), 20), Integer.parseInt(args[5]),
                        Double.parseDouble(args[4])), args.length == 7);
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (crew(e) instanceof LivingEntity le) {
                    afterBlasts.put(le.getUniqueId(), b);
                    n++;
                }
            }
            sender.sendMessage("Afterblast: " + n + " units");
            return true;
        }
        if (args.length >= 2 && args[0].equals("allies")) {            // the alliances of the players (#1315)
            ALLIES.clear();
            for (int i = 1; i < args.length; i++) {
                if (!args[i].equals("-")) {
                    String[] teams = args[i].split(",");
                    for (String t : teams) {
                        ALLIES.put(t, teams[0]);
                    }
                }
            }
            sender.sendMessage("Allies: " + ALLIES);
            return true;
        }
        if ((args.length == 3 || args.length == 5) && args[0].equals("arrows")) {   // a garrison adds arrows (#1113)
            try {                                                     // pass part: the arrows pass through (#4282)
                arrows.put(UUID.fromString(args[1]), Math.max(0, Integer.parseInt(args[2])));
                if (args.length == 5) {
                    fortPass.put(UUID.fromString(args[1]), new double[] {Double.parseDouble(args[3]), Double.parseDouble(args[4])});
                }
            } catch (IllegalArgumentException e) {                    // also NumberFormatException
                sender.sendMessage("Bad value: " + e.getMessage());
                return true;
            }
            sender.sendMessage("Arrows: " + args[2]);
            return true;
        }
        if (args.length == 3 && args[0].equals("ballistics")) {        // the arrows lead a moving target (#1549)
            if (args[2].equals("on")) {
                BALLISTICS.add(args[1]);
            } else {
                BALLISTICS.remove(args[1]);
            }
            sender.sendMessage("Ballistics: " + BALLISTICS);
            return true;
        }
        if (args.length >= 2 && args[0].equals("batch")) {              // many commands in one round trip (#2761)
            if (quiet == null) {
                quiet = Bukkit.createCommandSender(feedback -> { });
            }
            int n = 0;
            for (int i = 1; i < args.length; i++) {
                try {                                                    // one bad command must not drop the rest (#5443)
                    n += Bukkit.dispatchCommand(quiet, text(args[i])) ? 1 : 0;
                } catch (RuntimeException e) {
                    getLogger().warning("Batch command " + i + " failed: " + e);
                }
            }
            sender.sendMessage("Batch: " + n + "/" + (args.length - 1));
            return true;
        }
        if (args.length >= 2 && args[0].equals("camera")) {             // the camera mode (Camera.java)
            return cameraMode.command(sender, args, players(sender, args[1]));
        }
        if (args.length == 7 && args[0].equals("charge")) {            // Siphons (#2165)
            return charges(sender, args[1], charges, args[2], args[3], args[4], args[5], args[6], false);
        }
        if ((args.length == 4 || args.length == 6) && args[0].equals("chargeattack")) {   // Comitatenses (#4370)
            int[] c;
            Blast b;
            try {
                c = new int[] {Integer.parseInt(args[2]), Integer.parseInt(args[3])};
                b = args.length == 6 ? new Blast(Double.parseDouble(args[4]), Double.parseDouble(args[5]), 0, false) : null;
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad value: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                meleeCharges.put(e.getUniqueId(), c);
                meleeBlasts.compute(e.getUniqueId(), (k, v) -> b);
                if (rider(e) instanceof Mob r) {
                    meleeCharges.put(r.getUniqueId(), c);        // the rider of a mounted unit hits (#710)
                    meleeBlasts.compute(r.getUniqueId(), (k, v) -> b);
                }
                n++;
            }
            sender.sendMessage("Charge attack: " + n + " units");
            return true;
        }
        if (args.length >= 6 && args.length <= 8 && args[0].equals("chargedvolley")) {   // Xianbei Raider (#4546)
            ChargedVolley c;
            try {
                c = new ChargedVolley(Integer.parseInt(args[2]), Integer.parseInt(args[3]), new Stats(
                        Integer.parseInt(args[4]), 0, 0, true, true, Set.of(), bonus(args[5]), 0, 1.0, 1.0, Map.of(),
                        args.length > 7 && args[7].equals("1"), 0, 0.0),
                        args.length > 6 ? Double.parseDouble(args[6]) : 0);
            } catch (NumberFormatException | ArrayIndexOutOfBoundsException e) {
                sender.sendMessage("Bad value: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (rider(e) instanceof RangedEntity) {
                    e = rider(e);                                // a mounted archer: the rider shoots (#710)
                }
                chargedVolleys.put(e.getUniqueId(), c);
                n++;
            }
            sender.sendMessage("Charged volley: " + n + " units");
            return true;
        }
        if (args.length == 2 && args[0].equals("cheats")) {
            return cheats.command(sender, args);
        }
        if ((args.length == 2 || args.length == 3 && args[1].equals("heat")) && args[0].equals("deathmarks")) {        // the marks of the live replay (#846)
            return deaths.command(sender, args);
        }
        if (args.length == 2 && args[0].equals("destroy")) {           // the cheats torpedo, black death (#819)
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                Building b = buildings.get(e.getUniqueId());
                if (b != null) {                                  // it falls as at 0 hit points
                    hit(e, b, b.max());
                    n++;
                }
            }
            sender.sendMessage("Destroy: " + n + " buildings");
            return true;
        }
        if ((args.length == 5 || args.length == 6 && args[5].equals("foes")) && args[0].equals("detonate")) {
            // Incendiaries (#2165); foes: Thunderclap Bombs (#4367)
            return charges(sender, args[1], detonations, "0", args[2], "1", args[3], args[4], args.length == 6);
        }
        if (args.length >= 2 && args[0].equals("elevation")) {         // the damage from higher ground (#2307)
            try {
                int step = Integer.parseInt(args[1]);
                Map<String, double[]> f = new HashMap<>();
                for (int i = 2; i < args.length; i++) {
                    String[] t = args[i].split(":");
                    f.put(t[0], new double[] {Double.parseDouble(t[1]), Double.parseDouble(t[2]), Double.parseDouble(t[3])});
                }
                elevationStep = step;
                ELEVATION.clear();
                ELEVATION.putAll(f);
            } catch (RuntimeException e) {                     // a bad number or a team without three factors
                sender.sendMessage("Bad value: " + e.getMessage());
                return true;
            }
            sender.sendMessage("Elevation: " + elevationStep + " blocks, " + ELEVATION.size() + " teams");
            return true;
        }
        if (args.length == 8 && args[0].equals("gate")) {              // the portcullis of a gate (#1325, #1656)
            return gates.command(sender, args);
        }
        if (args.length == 4 && args[0].equals("gate")) {              // lock and unlock a gate (#2762)
            return gates.lock(sender, args);
        }
        if (args.length >= 2 && args[0].equals("minimap")) {           // #1237, #1238, #1567
            return minimap.command(sender, args);
        }
        if (args.length >= 2 && args[0].startsWith("box")) {            // the border of the selection box (#795)
            return border.command(sender, args, players(sender, args[1]));
        }
        if (args.length >= 2 && args[0].equals("neutral")) {           // the neutral stances of the players (#1645)
            NEUTRAL.clear();
            for (int i = 1; i < args.length; i++) {
                String[] st = args[i].split(":");
                if (st.length == 2) {
                    NEUTRAL.put(st[0], Set.of(st[1].split(",")));
                }
            }
            sender.sendMessage("Neutral: " + NEUTRAL);
            return true;
        }
        if (args.length >= 5 && args[0].equals("moveto")) {
            double x, y, z, speed;
            try {
                x = Double.parseDouble(args[2]);
                y = Double.parseDouble(args[3]);
                z = Double.parseDouble(args[4]);
                speed = args.length > 5 ? Double.parseDouble(args[5]) : 1.0;
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                Mob mob = unit(e);
                if (mob == null) {
                    continue;
                }
                Location goal = new Location(mob.getWorld(), x, y, z);
                grounds.remove(mob.getUniqueId());                     // a new order ends an attack ground (#4078)
                reach(mob, goal);
                setTarget(mob, null);
                if (rider(mob) != null) {
                    setTarget(rider(mob), null);
                }
                if (gates.any()) {                                     // through an own gate (#1325, #1656)
                    gates.raise(mob, goal);
                }
                dry(mob, goal);
                mob.getPathfinder().moveTo(goal, speed);
                orders.put(mob.getUniqueId(), new Order(goal, speed));
                n++;
            }
            sender.sendMessage("Moved " + n + " units");
            return true;
        }
        if (args.length == 2 && args[0].equals("stance")) {
            for (Entity e : select(sender, args[1])) {
                sender.sendMessage("Stance: " + stances.getOrDefault(e.getUniqueId(), "aggressive"));
                return true;
            }
            sender.sendMessage("Stance: no unit");
            return true;
        }
        if (args.length == 3 && args[0].equals("stance")) {
            if (!STANCES.contains(args[2])) {
                sender.sendMessage("Bad stance: " + args[2]);
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (e instanceof Mob || e instanceof Minecart || e instanceof Boat) {   // a siege unit: its minecart (#1820); a ship: its boat (#3018)
                    held.remove(e.getUniqueId());
                    posts.remove(e.getUniqueId());
                    if (args[2].equals("aggressive")) {
                        stances.remove(e.getUniqueId());
                    } else {
                        stances.put(e.getUniqueId(), args[2]);
                    }
                    n++;
                }
            }
            sender.sendMessage("Stance: " + n + " units");
            return true;
        }
        if (args.length >= 9 && args[0].equals("stats")) {
            double hp;
            Stats st;
            Dot.Rule dot = null;
            double far = 0.0;                              // the melee reach in blocks (#5242)
            try {
                hp = Double.parseDouble(args[2]);
                double taken = 1.0, friendly = 1.0, reflect = 0.0;
                Map<String, Integer> less = Map.of();
                boolean ignore = false;
                int rage = 0;
                for (int i = 10; i < args.length; i++) {   // the optional fields: key=value in any order (#4460)
                    String[] kv = args[i].split("=", 2);
                    String v = kv.length == 2 ? kv[1] : "";
                    switch (kv[0]) {
                        case "taken" -> taken = Double.parseDouble(v);          // the bonus damage taken (#2248)
                        case "friendly" -> friendly = Double.parseDouble(v);    // the friendly fire taken (#2418)
                        case "less" -> less = bonus(v);                         // Royal Heirs (#4331)
                        case "ignore" -> ignore = v.equals("1");                // Wootz Steel (#4331)
                        case "rage" -> rage = Integer.parseInt(v);              // Hamask (#4332)
                        case "reflect" -> reflect = Double.parseDouble(v);      // Lamellar Armor (#4332)
                        case "reach" -> far = Double.parseDouble(v);            // the melee reach in blocks (#5242)
                        case "dot" -> {                                         // damage:ticks:classes (#4339)
                            String[] d = v.split(":", 3);
                            dot = new Dot.Rule(Double.parseDouble(d[0]), Math.max(1, Integer.parseInt(d[1])),
                                    d[2].equals("-") ? Set.of() : Set.of(d[2].split(",")));
                        }
                        default -> throw new IllegalArgumentException("unknown field " + args[i]);
                    }
                }
                st = new Stats(Integer.parseInt(args[3]), Integer.parseInt(args[4]), Integer.parseInt(args[5]),
                        !args[6].equals("0"), args[6].equals("1"), args[7].equals("-") ? Set.of() : Set.of(args[7].split(",")),
                        bonus(args[8]), args.length >= 10 ? Integer.parseInt(args[9]) : 20,
                        taken, friendly, less, ignore, rage, reflect);
            } catch (RuntimeException e) {                 // a bad number or a bonus without ":"
                sender.sendMessage("Bad value: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                Entity t = crew(e);
                if (t instanceof LivingEntity le) {                // a siege unit or a ship: its crew takes the hits (#836, #1386)
                    AttributeInstance max = le.getAttribute(Attribute.MAX_HEALTH);
                    if (max != null) {                     // keep the lost hit points, as AoE2 does for Bloodlines (#940)
                        double lost = Math.max(0, max.getValue() - le.getHealth());
                        max.setBaseValue(hp);
                        le.setHealth(Math.min(max.getValue(), Math.max(Math.min(1, hp), hp - lost)));
                    }
                    stats.put(le.getUniqueId(), st);
                    dots.set(le.getUniqueId(), dot);
                    if (far > 0) reaches.put(le.getUniqueId(), far); else reaches.remove(le.getUniqueId());
                    nameLine(le);
                    Mob r = rider(le);
                    if (r != null) {
                        stats.put(r.getUniqueId(), st);          // its hits take the AoE2 attack (#710)
                        dots.set(r.getUniqueId(), dot);
                        if (far > 0) reaches.put(r.getUniqueId(), far); else reaches.remove(r.getUniqueId());
                    }
                    n++;
                }
            }
            sender.sendMessage("Stats: " + n + " units");
            return true;
        }
        if (args.length == 3 && args[0].equals("range") && args[2].equals("off")) {   // melee mode (#4504)
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (sailors(rider(e)) instanceof Mob mob) {
                    ranges.remove(mob.getUniqueId());
                    Bukkit.getMobGoals().removeGoal(mob, rangeKey);
                    if (mob.hasAI()) {
                        unit(mob);                               // its melee goals again
                    }
                    n++;
                }
            }
            sender.sendMessage("Range: " + n + " units");
            return true;
        }
        if (args.length >= 4 && args.length <= 8 && args[0].equals("range")) {
            Range r;
            boolean mobShot = args.length >= 5 && args[4].equals("-");   // no blast: the mob shoots (#1638)
            try {
                r = new Range(Double.parseDouble(args[2]), Integer.parseInt(args[3]),
                        args.length >= 5 && !mobShot ? Double.parseDouble(args[4]) : 0, args.length >= 5 && !mobShot,
                        args.length >= 6 ? Double.parseDouble(args[5]) : 0,
                        args.length >= 7 ? Double.parseDouble(args[6]) : 0,
                        args.length == 8 ? Double.parseDouble(args[7]) : 0.5);
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (rider(e) instanceof RangedEntity) {
                    e = rider(e);                                // a mounted archer: the rider shoots (#710)
                }
                e = sailors(e);                                     // a ship: its crew shoots (#1386)
                if (e instanceof Minecart cart && r.siege) {
                    ranges.put(cart.getUniqueId(), r);           // its carrier shoots (unit())
                    Mob c = carrier(cart, false);
                    if (c != null) {
                        Bukkit.getMobGoals().removeGoal(c, rangeKey);
                        if (c.hasAI()) {
                            unit(c);                             // a carrier in a fight keeps shooting (#3011)
                        }
                    }
                    n++;
                } else if (e instanceof Mob mob && (mob instanceof RangedEntity || r.siege)) {
                    ranges.put(mob.getUniqueId(), r);
                    Bukkit.getMobGoals().removeGoal(mob, rangeKey);
                    if (mob.hasAI()) {        // the goal again with the new range: a unit in a fight keeps shooting (#3011)
                        unit(mob);
                    }                         // no AI: the next order adds it
                    n++;
                }
            }
            sender.sendMessage("Range: " + n + " units");
            return true;
        }
        if (args.length == 3 && args[0].equals("sees")) {
            var who = players(sender, args[1]);
            Entity e;
            try {
                e = Bukkit.getEntity(UUID.fromString(args[2]));
            } catch (IllegalArgumentException x) {
                e = null;
            }
            sender.sendMessage("Sees: " + (!who.isEmpty() && e != null && who.get(0).canSee(e) ? 1 : 0));
            return true;
        }
        if ((args.length == 3 || args.length == 4 && Set.of("only", "first").contains(args[3]))
                && args[0].equals("sight")) {
            double r;
            try {
                r = Double.parseDouble(args[2]);
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                Entity c = crew(e);
                if ((c instanceof Mob || e instanceof Minecart) && stats.containsKey(c.getUniqueId())) {
                    UUID id = (e instanceof Minecart ? e : c).getUniqueId();   // a siege unit: its minecart; a ship: its crew
                    sights.put(id, r);
                    if (args.length == 4) {
                        modes.put(id, args[3]);
                    } else {
                        modes.remove(id);
                    }
                    n++;
                }
            }
            sender.sendMessage("Sight: " + n + " units");
            return true;
        }
        if (args.length >= 3 && args[0].equals("sightedge")) {          // the edge of the line of sight (#3330)
            return sight.command(sender, args, args[1].equals("count") ? List.of() : players(sender, args[1]));
        }
        Dot.Rule fortDot = null;                             // the last field dot=damage:ticks:classes (Curare, #4641)
        if (args.length >= 12 && args[0].equals("building") && args[args.length - 1].startsWith("dot=")) {
            String[] d = args[args.length - 1].substring(4).split(":", 3);
            try {
                fortDot = new Dot.Rule(Double.parseDouble(d[0]), Math.max(1, Integer.parseInt(d[1])),
                        d.length < 3 || d[2].equals("-") ? Set.of() : Set.of(d[2].split(",")));
            } catch (RuntimeException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            args = Arrays.copyOf(args, args.length - 1);
        }
        if ((args.length == 11 || args.length == 12 || args.length >= 15 && args.length <= 18) && args[0].equals("building")) {
            int hp;
            double range = 0, min = 0;
            Stats st;
            String box;
            int[] b = new int[6];
            try {
                hp = Integer.parseInt(args[2]);
                boolean shoots = args.length >= 15;          // attack, range in blocks, reload in ticks (#1111), min (#1546)
                Set<String> classes = args.length == 12 || args.length >= 16   // the classes after the attack (#1419)
                        ? Set.of(args[args.length == 12 ? 11 : 15].split(",")) : Set.of("building", "standard");
                st = new Stats(shoots ? Integer.parseInt(args[11]) : 0, Integer.parseInt(args[3]),
                        Integer.parseInt(args[4]), shoots, true, classes,
                        args.length >= 17 && !args[16].equals("-") ? bonus(args[16]) : Map.of(),   // Heated Shot (#1548)
                        shoots ? Integer.parseInt(args[13]) : 0,
                        args.length == 18 ? Double.parseDouble(args[17]) : 1.0, 1.0);   // the bonus damage taken (#4281)
                range = shoots ? Double.parseDouble(args[12]) : 0;
                min = shoots ? Double.parseDouble(args[14]) : 0;
                var c = new ArrayList<String>();
                for (int i = 5; i < 11; i++) {
                    b[i - 5] = Integer.parseInt(args[i]);
                    c.add(Integer.toString(b[i - 5]));
                }
                box = String.join(" ", c);
            } catch (RuntimeException e) {                 // a bad number or a bonus without ":"
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (e instanceof LivingEntity le) {
                    le.setCollidable(false);                  // units walk up to the walls, not off the slime
                    le.setFireTicks(0);                       // it can stand in lava before this command (#1526)
                    buildings.put(le.getUniqueId(), new Building(st, box, hp, b, range, min));
                    dots.set(le.getUniqueId(), fortDot);       // the arrows of the building (Curare, #4641)
                    hp().getScoreFor(le).setScore(hp);
                    n++;
                }
            }
            sender.sendMessage("Buildings: " + n);
            return true;
        }
        if (args.length == 2 && args[0].equals("goals")) {
            var found = select(sender, args[1]);
            if (found.isEmpty() || !(found.get(0) instanceof Mob mob)) {
                sender.sendMessage("No unit");
                return true;
            }
            var keys = new ArrayList<String>();
            for (var g : Bukkit.getMobGoals().getAllGoals(mob)) {
                keys.add(g.getKey().getNamespacedKey().getKey());
            }
            sender.sendMessage("Goals: " + String.join(" ", keys));
            return true;
        }
        if (args.length >= 3 && args[0].equals("heatmap")) {         // #5457
            return Heatmap.command(sender, args);
        }
        if (args.length >= 3 && (args[0].equals("hide") || args[0].equals("show"))) {   // one command per second (#1302)
            boolean hide = args[0].equals("hide");
            boolean view = args[2].equals("view");                     // only these players (#2901)
            var who = players(sender, args[1]);
            String team = selectorTeam(args[1]);
            int n = 0;
            if (hide && args[2].equals("team")) {                  // the hides of the own team only (#3070)
                for (var u : hidden.keySet()) {
                    Entity e = Bukkit.getEntity(u);
                    if (e != null) {
                        for (Player p : who) {
                            if (hiddenFor(p, u)) {
                                see(p, e, false);
                            } else {
                                see(p, e, true);
                            }
                        }
                        n++;
                    }
                }
                sender.sendMessage("Hidden: " + n + " entities, " + who.size() + " players");
                return true;
            }
            if (!hide && args[2].equals("all")) {                  // a spectator sees through the fog of all teams (#2921)
                for (var h : hidden.entrySet()) {
                    Entity e = Bukkit.getEntity(h.getKey());
                    if (e != null && !h.getValue().contains(ALL)) {
                        who.forEach(p -> see(p, e, true));
                        n++;
                    }
                }
                sender.sendMessage("Shown: " + n + " entities, " + who.size() + " players");
                return true;
            }
            for (int i = 2; i < args.length; i++) {
                UUID u;
                try {
                    u = UUID.fromString(args[i]);
                } catch (IllegalArgumentException e) {
                    continue;
                }
                if (view) {
                    // the global set stays: the minimap dots and the players that join later (#2901)
                } else if (hide) {
                    hidden.computeIfAbsent(u, k -> new HashSet<>()).add(team);
                } else if (team.equals(ALL) || hidden.containsKey(u) && hidden.get(u).remove(team) && hidden.get(u).isEmpty()) {
                    hidden.remove(u);
                }
                Entity e = Bukkit.getEntity(u);
                if (e == null) {
                    continue;
                }
                for (Player p : who) {
                    if (hide) {
                        see(p, e, false);
                    } else {
                        see(p, e, true);
                    }
                }
                n++;
            }
            sender.sendMessage((hide ? "Hidden: " : "Shown: ") + n + " entities, " + who.size() + " players");
            return true;
        }
        if (args.length == 1 && args[0].equals("hits")) {            // the battle music (#5342, game/music.py)
            sender.sendMessage(alerts.hits());
            return true;
        }
        if (args.length == 3 && args[0].equals("speed")) {          // the attribute command fails on a minecart (#836)
            double v;
            try {
                v = Double.parseDouble(args[2]);
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad speed: " + args[2]);
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                Mob mob = unit(e);
                AttributeInstance a = mob == null ? null : mob.getAttribute(Attribute.MOVEMENT_SPEED);
                if (a != null) {
                    a.setBaseValue(v);
                    n++;
                }
            }
            sender.sendMessage("Speed: " + n + " units");
            return true;
        }
        if (args.length == 2 && args[0].equals("stop")) {
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (walker(e) instanceof Mob mob) {
                    orders.remove(mob.getUniqueId());
                    grounds.remove(mob.getUniqueId());
                    posts.remove(mob.getUniqueId());
                    mob.getPathfinder().stopPathfinding();
                    mob.setAI(false);
                    if (rider(mob) != null) {
                        setTarget(rider(mob), null);
                    }
                    n++;
                }
            }
            sender.sendMessage("Stopped " + n + " units");
            return true;
        }
        if (args.length == 6 && args[0].equals("throw")) {             // Gothikon (#4368)
            Throw w;
            try {
                w = new Throw(Math.max(1, Integer.parseInt(args[2])), Integer.parseInt(args[3]),
                        Double.parseDouble(args[4]), Integer.parseInt(args[5]));
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (e instanceof Mob mob) {
                    throwers.put(mob.getUniqueId(), w);
                    axes.remove(mob.getUniqueId());
                    n++;
                }
            }
            sender.sendMessage("Throw: " + n + " units");
            return true;
        }
        if (args.length == 2 && args[0].equals("unwear")) {            // a redraw after a wall technology (#3071)
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (wear.remove(e.getUniqueId()) != null) {
                    n++;
                }
            }
            sender.sendMessage("Unwear: " + n + " buildings");
            return true;
        }
        if (args.length >= 3 && args[0].equals("menu")) {
            return menu(sender, args);
        }
        if (args.length >= 3 && args[0].equals("menu-add")) {
            return menuAdd(sender, args);
        }
        if (args.length == 2 && args[0].equals("menu-close")) {
            int n = 0;
            for (Player p : players(sender, args[1])) {
                if (menuOf(p) != null) {
                    p.closeInventory();
                    n++;
                }
            }
            sender.sendMessage("Closed: " + n + " menus");
            return true;
        }
        if (args.length == 4 && args[0].equals("view")) {             // the "Go to" menu (#1830, game/goto.py)
            int n = 0;
            for (Player p : players(sender, args[1])) {
                double x = Double.parseDouble(args[2]), z = Double.parseDouble(args[3]);
                int top = p.getWorld().getHighestBlockYAt((int) Math.floor(x), (int) Math.floor(z));
                Alerts.view(p, new Location(p.getWorld(), x, top + 1, z));
                n++;
            }
            sender.sendMessage("View: " + n + " players");
            return true;
        }
        if (args.length == 4 && args[0].equals("volley")) {           // the Armenian galleys and dromons (#2379)
            int[] v;
            try {
                v = new int[] {Integer.parseInt(args[2]), Integer.parseInt(args[3])};
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (rider(e) instanceof RangedEntity) {
                    e = rider(e);                                // a mounted archer: the rider shoots (#710)
                }
                e = crew(e);                          // a ship: its crew shoots (#1386); a siege unit: its crew (#4338)
                if (e instanceof LivingEntity le) {
                    volleys.put(le.getUniqueId(), v);
                    n++;
                }
            }
            sender.sendMessage("Volley: " + n + " units");
            return true;
        }
        if (args.length == 5 && args[0].equals("vsunits")) {          // the Lou Chuan (#4505)
            VsUnits v;
            try {
                v = new VsUnits(Integer.parseInt(args[2]), bonus(args[3]), Double.parseDouble(args[4]));
            } catch (RuntimeException e) {                 // a bad number or a bonus without ":"
                sender.sendMessage("Bad value: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                for (Entity t : new Entity[] {e, crew(e), rider(e)}) {   // the ship and its crew, as aoe stats
                    if (t != null) {
                        vsUnits.put(t.getUniqueId(), v);
                    }
                }
                n++;
            }
            sender.sendMessage("Vsunits: " + n + " units");
            return true;
        }
        if ((args.length == 2 || args.length == 3) && args[0].equals("where")) {
            // One answer for many units: one `data get entity` for each unit costs too many commands (#813). A page
            // keeps the answer below the 4096 bytes of one RCON packet.
            int from;
            try {
                from = args.length > 2 ? Integer.parseInt(args[2]) : 0;
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            var found = new ArrayList<>(select(sender, args[1]));
            found.sort(java.util.Comparator.comparing(e -> e.getUniqueId().toString()));
            var parts = new ArrayList<String>();
            for (Entity e : found.subList(Math.min(from, found.size()), Math.min(from + WHERE_PAGE, found.size()))) {
                Location l = e.getLocation();
                Mob f = e instanceof Mob mob ? (rider(mob) != null ? rider(mob) : mob) : null;   // a rider has the target (#1334)
                parts.add(String.format(java.util.Locale.ROOT, "%s %.2f %.2f %.2f %d %d", e.getUniqueId(), l.getX(),
                        l.getY(), l.getZ(), orders.containsKey(e.getUniqueId()) ? 1 : 0,
                        fought.remove(e.getUniqueId()) | (f != null && target(f) != null) ? 1 : 0));
            }
            sender.sendMessage("Where " + found.size() + ": " + String.join(", ", parts));
            return true;
        }
        if (args.length >= 2 && args[0].equals("label")) {
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                e = crew(e);                                 // a siege unit or a ship: its crew has the name line (#1352, #3086)
                if (args.length > 2) {                       // a new name keeps the player color of the old one (#941)
                    if (!names.containsKey(e.getUniqueId())) {
                        nameLine(e);                         // the old name of the converter, with its color
                    }
                    Component old = names.get(e.getUniqueId());
                    names.put(e.getUniqueId(), Component.text(String.join(" ", List.of(args).subList(2, args.length)),
                            old == null ? (e.customName() == null ? null : e.customName().color()) : old.color()));
                }
                if (names.containsKey(e.getUniqueId())) {
                    nameLine(e);
                    n++;
                }
            }
            sender.sendMessage("Label: " + n + " units");
            return true;
        }
        if ((args.length == 4 || args.length == 5) && args[0].equals("lore")) {
            HELP.put(args[1] + ":" + text(args[2]), text(args[3]));
            if (args.length == 5) {
                KEYS.put(args[1] + ":" + text(args[2]), args[4]);
            }
            sender.sendMessage("Lore: " + HELP.size() + " items");
            return true;
        }
        if (args.length == 3 && args[0].equals("attack")) {
            List<Entity> targets = select(sender, args[2]);
            if (targets.isEmpty() || !(crew(targets.get(0)) instanceof LivingEntity target)) {   // a ship or a siege unit: its crew
                sender.sendMessage("No target");
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                Mob mob = unit(e);
                if (mob != null && afloat(target) && !(mob.getVehicle() instanceof Boat)
                        && !ranged(rider(mob) != null ? rider(mob) : mob)) {
                    continue;                                    // a land melee unit cannot reach a ship (#1658)
                }
                if (mob != null && mob != target && !sameTeam(mob, target)) {
                    orders.remove(mob.getUniqueId());
                    grounds.remove(mob.getUniqueId());
                    posts.remove(mob.getUniqueId());            // an order: a defensive unit chases to the end
                    Mob r = rider(mob);
                    if (r != null) {                             // the horse has no attack goal: the rider leads
                        setTarget(mob, null);
                        mob.getPathfinder().stopPathfinding();
                        mob = unit(r);
                    }
                    reach(mob, target.getLocation());
                    setTarget(mob, target);
                    held.remove(mob.getUniqueId());             // an order: the unit walks, also with stand ground
                    n++;
                }
            }
            sender.sendMessage("Attack: " + n + " units");
            return true;
        }
        if (args.length == 5 && args[0].equals("attackground")) {       // Attack Ground (#4078)
            Location at;
            try {
                at = new Location(null, Double.parseDouble(args[2]), Double.parseDouble(args[3]), Double.parseDouble(args[4]));
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                Mob mob = unit(e);
                Range r = mob == null ? null : ranges.get(mob.getUniqueId());
                if (r == null && mob != null && mob.getScoreboardTags().contains(CARRIER) && !mob.getPassengers().isEmpty()) {
                    r = ranges.get(mob.getPassengers().get(0).getUniqueId());   // a carrier: the range of its siege unit
                }
                if (r != null && r.siege) {                     // the Mangonel line, and the other siege shots
                    orders.remove(mob.getUniqueId());
                    posts.remove(mob.getUniqueId());
                    setTarget(mob, null);
                    at.setWorld(mob.getWorld());
                    grounds.put(mob.getUniqueId(), at.clone());
                    held.remove(mob.getUniqueId());             // an order: the unit walks, also with stand ground
                    n++;
                }
            }
            sender.sendMessage("Attack ground: " + n + " units");
            return true;
        }
        return false;
    }
}
