package aoe2mc;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

import org.bukkit.Bukkit;
import org.bukkit.HeightMap;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.block.data.BlockData;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.AbstractArrow;
import org.bukkit.entity.AbstractSkeleton;
import org.bukkit.entity.Arrow;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Minecart;
import org.bukkit.entity.Mob;
import org.bukkit.entity.Pig;
import org.bukkit.entity.Pillager;
import org.bukkit.entity.Player;
import org.bukkit.entity.Projectile;
import org.bukkit.entity.Villager;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.EntityRegainHealthEvent;
import org.bukkit.event.entity.EntityTargetEvent;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scoreboard.Criteria;
import org.bukkit.scoreboard.Objective;
import org.bukkit.scoreboard.Scoreboard;
import org.bukkit.scoreboard.Team;
import org.bukkit.util.Vector;

import com.destroystokyo.paper.entity.Pathfinder;
import com.destroystokyo.paper.entity.RangedEntity;
import com.destroystokyo.paper.entity.ai.Goal;
import com.destroystokyo.paper.entity.ai.GoalKey;
import com.destroystokyo.paper.entity.ai.GoalType;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;

/**
 * Orders for the units of the game program, with Minecraft path finding (#435). Vanilla has no command for
 * "walk to this point", so this plugin gives one to RCON:
 *   aoe moveto <selector> <x> <y> <z> [speed]   walk on the path of Mob#getPathfinder
 *   aoe arrows <uuid> <n>                      the arrows of each shot of a building: its base (an empty town center
 *                                              0, #1201) and 1 for each garrisoned villager or foot archer (#1113,
 *                                              game/garrison.py); 0: it does not shoot. Default 1
 *   aoe attack <selector> <target selector>    Mob#setTarget: the mob attacks with its own AI
 *   aoe goals <selector>                       the goals of the first unit (#436), for checks
 *   aoe stance <selector> <aggressive|defensive|stand_ground|no_attack>
 *                                              the AoE2 stance of a unit (#1104): no_attack never attacks without an
 *                                              order, stand_ground attacks only an enemy in its range and does not walk,
 *                                              defensive chases an enemy only CHASE blocks past its range (#1105)
 *   aoe stance <selector>                      the stance of the first unit (#1107), for checks
 *   aoe stats <selector> <hp> <attack> <melee armor> <pierce armor> <ranged 0|1|2> <classes|-> <class:bonus,...|->
 *             [reload ticks]                   the AoE2 values of a unit (#514, game/combat.py stats_command); a melee
 *                                              unit hits once per reload (#848, default 20: the vanilla cooldown)
 *   aoe stop <selector>                        stop the walk and turn the AI off: the unit stands still (#437)
 *   aoe range <selector> <blocks> <ticks> [blast]
 *                                              a ranged unit shoots from this range, one shot per ticks (#515); a
 *                                              shot with a blast radius in blocks hits all units near the target, and
 *                                              a siege unit (a minecart) shoots too (#1050); blast 0: a siege shot
 *                                              that hits only the target (the Scorpion, #1062)
 *   aoe sight <selector> <blocks>              an idle unit attacks an enemy in this line of sight (#775)
 *   aoe building <selector> <hp> <melee armor> <pierce armor> <x0> <y0> <z0> <x1> <y1> <z1>
 *                                              make the entity the target of a building (#517, combat.building)
 *   aoe building ... <attack> <range> <reload> the building shoots arrows: range in blocks, reload in ticks (#1111)
 *   aoe menu <player> <title> <slot>:<material>:<name>:<lore>[:<count>] ...
 *                                              open a chest menu (#619, game/menu.py; the texts are URL-encoded)
 *   aoe menu-close <player>                    close the menu of the player
 *   aoe cheats <code>,<code>,...|-             the AoE2 cheat codes in the chat (#816, Cheats.java; URL-encoded)
 *   aoe deathmarks on|off                      a short mark where a replay unit dies (#846, Deaths.java)
 *   aoe destroy <selector>                     the buildings fall as at 0 hit points: "Destroy: <n> buildings" (#819)
 *   aoe label <selector> [name]                show the name line again (after a selection change); a name sets
 *                                              the name of a building target (#661)
 *   aoe lore <material> <name> <text>          the last lore line of each menu item with this material and name: the
 *                                              AoE2 help text (#1160, train.HELP; URL-encoded). Sent once at the
 *                                              setup, so the menu commands stay below the RCON limit
 *   aoe minimap on|off|pixel <x> <z>           the live units as dots in their team color on map 0, once per
 *                                              second (#1237, Minimap.java); pixel: the map pixel of a block
 *   aoe where <selector> [from]                "Where <count>: <uuid> <x> <y> <z> <order 0|1> <target 0|1>, ..." for
 *                                              WHERE_PAGE units from index `from` in UUID order (#813, tools/replay_drift.py);
 *                                              target 1 also after a target or a hit since the last answer (#1169)
 *   aoe speed <selector> <speed>               the movement_speed of each unit; a siege unit (a minecart) gets its
 *                                              carrier first (#836): an invisible small pig that walks for it
 *   aoe box <player> <x> <z> <dye>             draw the selection box from this corner to the look (#795, Border.java)
 *   aoe box-clear <player>                     end the border of the selection box
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
 * (no unit classes or no attack) and Gaia animals (no AoE2 values) do not attack back.
 * A unit with a line of sight (aoe sight) and the same rules also attacks the nearest enemy unit in its sight, each
 * second (#775). The vanilla goal nearest_attackable_target also chooses units of the own team, players and animals,
 * and has no AoE2 sight: tame() drops it.
 * A stance (aoe stance, #1104) changes only what a unit does without an order: "no attack" does not attack back and
 * does not attack an enemy in its sight; "stand ground" does so only for an enemy in its range (a melee unit: next to
 * it), keeps its place (RangeGoal shoots without a walk) and drops the target when it goes out of the range.
 * "defensive" (#1105) attacks as "aggressive" (the default), but keeps the place where its fight started: past its range
 * + CHASE from it, or when the target is dead, it drops the target and walks back there with an order (as aoe moveto).
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
 * A mounted unit (#710) is a horse (its UUID in aoe2mc.json) with a rider: a horse has no attack goal. The rider gets
 * the values of "aoe stats", the range of "aoe range" and the target of "aoe attack", and the horse gets AI without goals:
 * a riding mob walks with the navigation of its vehicle (vanilla Mob#getNavigation), so the horse follows the rider.
 * A hit on the rider takes the hit points of the horse, and the rider dies with the horse (#732).
 * A horse regenerates by itself in vanilla, an AoE2 unit does not: the plugin cancels the REGEN healing of a unit
 * with AoE2 values (#850). Other reasons (a later Monk heal) stay.
 * A building is blocks, and a mob attacks only a living entity: an invisible mob without AI (a slime of the size of
 * the footprint, game/combat.py building) stands in the building and takes the attacks, so that the vanilla attack
 * goals and paths work (#517). The plugin keeps the hit points of the building (a building has more than the
 * 1024 of max_health) in the scoreboard aoe_hp, cancels all other damage to it and from it (no suffocation in the
 * walls, no slime touch), and at 0 removes it and fills the box of the building with air. The vanilla melee goal
 * hits only a target in sight, and the eye of the slime is in the walls: so a unit next to the slime that has it as
 * target hits it once per AoE2 reload (Mob#attack, the vanilla hit with the swing; #848). A ranged unit shoots
 * a building from its range to the nearest side of the target, without sight of the eye (#608). Its arrow sticks
 * in the walls, so the goal takes the hit points for each shot, and an arrow that hits the slime does nothing.
 * Vanilla has no clickable item menu: "aoe menu" opens an inventory with the items (#619). A click on an item is
 * cancelled (the player takes nothing) and sets the score aoe_menu of the player to slot + 1 (a shift click: -(slot + 1),
 * #620); the menu stays open, so the player can click again. "aoe menu" on an open menu of the same title and size only changes the items.
 * The name line of a unit or building (#661, owner decision #658): the custom name of the mob holds the name and 5 hearts
 * ("Militia ❤❤❤❤❤", red: full, gray: empty, each heart 20 % of the hit points). It is visible only for a hurt unit or a
 * selected one (tag aoe2mc.selected, game/gather.py), as the bars in AoE2. Each hit and "aoe stats" update it.
 */
public final class AoePlugin extends JavaPlugin implements Listener {
    // ranged: the unit shoots; pierces: its hit takes the pierce armor (not so for a Throwing Axeman, #800);
    // reload: the ticks between two melee hits (#848)
    private record Stats(int attack, int melee, int pierce, boolean ranged, boolean pierces, Set<String> classes,
                         Map<String, Integer> bonus, int reload) {
        int damage(Stats t) {                                 // the same rule as game/combat.py damage()
            int bonus = 0;
            for (String c : t.classes) {
                bonus += this.bonus.getOrDefault(c, 0);
            }
            return Math.max(1, Math.max(0, attack - (pierces ? t.pierce : t.melee)) + bonus);
        }
    }

    private final Map<UUID, Stats> stats = new HashMap<>();
    private final Ghost ghost = new Ghost(this);
    private final Cheats cheats = new Cheats(this);
    private final Deaths deaths = new Deaths(this);
    private final Alerts alerts = new Alerts(this, AoePlugin::side);   // "under attack" for the team of the target (#1231)
    private final Minimap minimap = new Minimap(this);
    private final Viewer viewer = new Viewer(this);                 // the game mode switch of a replay viewer (#910)
    private final Border border = new Border();

    // b: x0 y0 z0 x1 y1 z1 of box; range: the blocks from the footprint that its arrows reach, 0: no attack (#1111)
    private record Building(Stats stats, String box, int max, int[] b, double range) {}

    private final Map<UUID, Building> buildings = new HashMap<>();
    private final Map<UUID, Integer> arrows = new HashMap<>();       // the arrows of a shot of a building (#1113)
    private final Map<UUID, Component> names = new HashMap<>();      // the name in the name line (#661)
    private static final int HEARTS = 5;
    private static final int WHERE_PAGE = 40;                          // aoe where: about 3000 bytes per answer
    private final Map<UUID, Integer> lastHit = new HashMap<>();      // tick of the last melee hit of a unit
    private final Set<UUID> fought = new HashSet<>();                 // a target or a hit since the last aoe where (#1169)
    private static final double REACH = Math.sqrt(2.04) - 0.6;       // vanilla melee reach past the hit box
    private static final double WALK = 43.4;      // blocks per second of movement_speed 1 on flat ground (game/ai.py)
    private static final double GROUND = 0.6 * 0.91;  // ground drag per tick (the friction of most blocks)
    private static final double LOOK = 3, OFF = 0.75;   // steer(): blocks ahead, blocks off the line (#1022)

    private static final class Order {
        final Location goal;
        final double speed;
        final int start = Bukkit.getCurrentTick();
        int fails;

        Order(Location goal, double speed) {
            this.goal = goal;
            this.speed = speed;
        }
    }

    private final Map<UUID, Order> orders = new HashMap<>();

    private record Range(double blocks, int ticks, double blast, boolean siege) {
    }

    private final Map<UUID, Range> ranges = new HashMap<>();
    private final Map<UUID, Double> sights = new HashMap<>();       // the line of sight of a unit in blocks (#775)
    private static final Set<String> STANCES = Set.of("aggressive", "defensive", "stand_ground", "no_attack");
    private final Map<UUID, String> stances = new HashMap<>();      // no entry: aggressive (#1104)
    private final Set<UUID> held = new HashSet<>();                 // stand ground units with a target of their own
    private final Map<UUID, Location> posts = new HashMap<>();      // defensive units in a fight: their place (#1105)
    // defensive: the blocks past its range that a unit chases. The AoE2 wiki ("Unit stance": "will follow for a certain
    // number of tiles before returning to their original position") gives no number: 3 tiles of 4 blocks (#1105).
    private static final double CHASE = 12.0;
    private static final double MELEE = 2.0;          // stand ground: the blocks to an enemy that a melee unit attacks
    static final String CARRIER = "aoe2mc.carrier";                  // the tag of the mob that carries a siege unit
    private static final double STEP = 1.25;                         // a step of 1 block with snow[layers=2] (#851)
    private static final double CARRIER_SCALE = 0.3;                 // a pig of 0.27 blocks: the minecart stays low
    private final GoalKey<Mob> rangeKey = GoalKey.of(Mob.class, new NamespacedKey("aoe2mc", "aoe_range"));
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
            LivingEntity t = mob.getTarget();
            return t != null && t.isValid() && !t.isDead();
        }

        @Override
        public void stop() {
            mob.getPathfinder().stopPathfinding();
        }

        @Override
        public void tick() {
            LivingEntity t = mob.getTarget();
            // a building: the range to its nearest side, and no sight of the eye of its target in the walls (#608)
            boolean wall = buildings.containsKey(t.getUniqueId());
            boolean near = (wall ? gap(mob, t) : mob.getLocation().distanceSquared(t.getLocation()))
                    <= range.blocks * range.blocks && (wall || mob.hasLineOfSight(t));
            if (near) {
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
                blast(mob, t, range.blast);
            } else if (now >= next && near && mob instanceof RangedEntity r) {
                if (mob instanceof AbstractSkeleton || mob instanceof Pillager) {
                    shoot(mob, t);            // the vanilla shot misses (#634), and fails for a crossbow (#633)
                } else {
                    r.rangedAttack(t, 1.0f);
                }
                next = now + range.ticks;
                Stats a = stats.get(mob.getUniqueId());
                Building b = buildings.get(t.getUniqueId());
                if (a != null && b != null) {           // the arrow sticks in the walls: the shot hits (#608)
                    hit(t, b, a.damage(b.stats));
                    hitEffect(t, b, mob);
                    alerts.hit(t, true, mob);
                }
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

    // The entity with the AoE2 values of a shooter: the crew of a siege unit for its carrier (aoe stats, #836).
    private static Entity crew(Mob mob) {
        return mob.getPassengers().isEmpty() || !(mob.getPassengers().get(0) instanceof Minecart cart)
                || cart.getPassengers().isEmpty() ? mob : cart.getPassengers().get(0);
    }

    // A blast shot (#1050): each unit with AoE2 values within r blocks of the target takes the AoE2 damage of the
    // shooter, also its own units. A mounted unit has the hit points of its horse (#732): only the horse counts.
    // r 0: a siege shot that hits only the target (#1062).
    private void blast(Mob mob, LivingEntity t, double r) {
        Entity from = crew(mob);
        Stats a = stats.get(from.getUniqueId());
        if (a == null) {
            return;
        }
        Building b = buildings.get(t.getUniqueId());
        Location at = t.getLocation();
        if (b != null) {                                  // a building takes the shot alone
            hit(t, b, a.damage(b.stats));
            hitEffect(t, b, mob);
            alerts.hit(t, true, mob);
        } else if (r <= 0) {
            LivingEntity v = t.getVehicle() instanceof LivingEntity h && stats.containsKey(h.getUniqueId()) ? h : t;
            if (v.isValid() && stats.containsKey(v.getUniqueId())) {
                harm(v, stats.get(v.getUniqueId()), a, from);
            }
            t.getWorld().spawnParticle(Particle.CRIT, at.clone().add(0, 1, 0), 8);
            t.getWorld().playSound(at, Sound.ENTITY_ARROW_HIT, 1.0f, 1.0f);
            return;
        } else {
            for (Entity e : t.getWorld().getNearbyEntities(at, r, r, r)) {
                if (e instanceof LivingEntity le && le.isValid() && stats.containsKey(le.getUniqueId())
                        && !buildings.containsKey(le.getUniqueId()) && le != from
                        && !(le.getVehicle() instanceof LivingEntity v && stats.containsKey(v.getUniqueId()))
                        && le.getLocation().distanceSquared(at) <= r * r) {
                    harm(le, stats.get(le.getUniqueId()), a, from);
                }
            }
        }
        t.getWorld().spawnParticle(Particle.EXPLOSION, at.clone().add(0, 0.5, 0), 1);
        t.getWorld().playSound(at, Sound.ENTITY_GENERIC_EXPLODE, 1.0f, 1.0f);
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

    private static void shoot(Mob mob, LivingEntity t) {
        Location from = mob.getEyeLocation();
        Vector to = t.getLocation().toVector().add(new Vector(0, t.getHeight() * 0.5, 0)).subtract(from.toVector());
        double ticks = to.length() / ARROW_SPEED;
        to.setY(to.getY() + 0.5 * ARROW_GRAVITY * ticks * ticks);
        Arrow a = mob.launchProjectile(Arrow.class, to.normalize().multiply(ARROW_SPEED));
        a.setPickupStatus(AbstractArrow.PickupStatus.DISALLOWED);
        boolean bow = mob.getEquipment().getItemInMainHand().getType() == Material.BOW;
        mob.getWorld().playSound(mob, bow ? Sound.ENTITY_SKELETON_SHOOT : Sound.ITEM_CROSSBOW_SHOOT, 1.0f, 1.0f);
    }

    // Each 2 ticks: a building with an attack (aoe building with attack, range and reload: a town center, a castle,
    // #1111) shoots one arrow per reload at the nearest unit of another team in its range. As in AoE2, the range counts
    // from the edge of its footprint. Each garrisoned villager or foot archer adds an arrow (aoe arrows, #1113): all
    // arrows of a shot go to the same target, as in AoE2. Not at a rider (its horse is the target), a garrisoned unit or a building.
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
                        && !buildings.containsKey(le.getUniqueId()) && !le.isInvulnerable() && le.getVehicle() == null
                        && !sameTeam(fort, le)) {
                    var p = le.getLocation();
                    double dx = Math.max(0, Math.max(b[0] - p.getX(), p.getX() - b[3] - 1));
                    double dz = Math.max(0, Math.max(b[2] - p.getZ(), p.getZ() - b[5] - 1));
                    if (dx * dx + dz * dz <= bestD) {
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
    // one shot do not fly as one; the start is above the highest block of the 3 x 3 columns around the point.
    private static void volley(LivingEntity fort, int[] b, LivingEntity t, int k) {
        var p = t.getLocation();
        Location from = new Location(fort.getWorld(), Math.max(b[0] + 0.5, Math.min(b[3] + 0.5, p.getX())), 0,
                Math.max(b[2] + 0.5, Math.min(b[5] + 0.5, p.getZ())));
        int top = b[1];
        for (int dx = -1; dx <= 1; dx++) {
            for (int dz = -1; dz <= 1; dz++) {
                top = Math.max(top, fort.getWorld().getHighestBlockYAt(from.getBlockX() + dx, from.getBlockZ() + dz,
                        HeightMap.MOTION_BLOCKING));
            }
        }
        from.add(k == 0 ? 0 : 0.6 * Math.cos(k * 2.4), 0, k == 0 ? 0 : 0.6 * Math.sin(k * 2.4));
        from.setY(top + 1.5 + 0.2 * (k % 3));
        Vector to = t.getLocation().toVector().add(new Vector(0, t.getHeight() * 0.5, 0)).subtract(from.toVector());
        double ticks = to.length() / ARROW_SPEED;
        to.setY(to.getY() + 0.5 * ARROW_GRAVITY * ticks * ticks);
        Arrow a = fort.getWorld().spawnArrow(from, to, (float) ARROW_SPEED, 0f);
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
            meta.displayName(Component.text(text(p[2])));
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

    @EventHandler
    public void onMenuClick(InventoryClickEvent ev) {
        if (!(ev.getView().getTopInventory().getHolder(false) instanceof Menu)) {
            return;
        }
        ev.setCancelled(true);                                         // also shift clicks from the own inventory
        int slot = ev.getRawSlot();
        if (slot >= 0 && slot < ev.getView().getTopInventory().getSize() && ev.getCurrentItem() != null
                && !ev.getCurrentItem().isEmpty()) {
            menuScore().getScore(ev.getWhoClicked().getName()).setScore(ev.isShiftClick() ? -(slot + 1) : slot + 1);
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
        Bukkit.getScheduler().runTaskTimer(this, this::steer, 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, ghost::tick, 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, border::tick, 4L, 4L);
        Bukkit.getScheduler().runTaskTimer(this, this::siege, 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, this::burn, 20L, 20L);
        Bukkit.getScheduler().runTaskTimer(this, this::watch, 20L, 20L);
        Bukkit.getScheduler().runTaskTimer(this, this::towers, 2L, 2L);
        Bukkit.getScheduler().runTaskTimer(this, this::hold, 4L, 4L);
        Bukkit.getPluginManager().registerEvents(this, this);
        Bukkit.getPluginManager().registerEvents(cheats, this);
        Bukkit.getPluginManager().registerEvents(deaths, this);
        Bukkit.getPluginManager().registerEvents(viewer, this);
    }

    @EventHandler(ignoreCancelled = true)
    public void onHit(EntityDamageByEntityEvent ev) {
        Entity from = ev.getDamager();
        if (from instanceof Projectile p && p.getShooter() instanceof Entity shooter) {
            from = shooter;
        }
        Stats a = stats.get(from.getUniqueId()), t = stats.get(ev.getEntity().getUniqueId());
        Building b = buildings.get(ev.getEntity().getUniqueId());
        Building fort = ev.getDamager() instanceof Projectile ? buildings.get(from.getUniqueId()) : null;
        if (fort != null && b == null && !sameTeam(from, ev.getEntity())) {
            a = fort.stats;                                   // the arrow of a town center or castle on a unit (#1111)
        } else if (buildings.containsKey(from.getUniqueId()) || b != null) {
            ev.setCancelled(true);
            if (a != null && b != null && !(ev.getDamager() instanceof Projectile) && ready(from, a)) {   // RangeGoal counts a shot
                lastHit.put(from.getUniqueId(), Bukkit.getCurrentTick());
                hit(ev.getEntity(), b, a.damage(b.stats));
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
        if (!(ev.getDamager() instanceof Projectile)) {      // a melee hit: once per AoE2 reload (#848)
            if (!ready(from, a)) {
                return;
            }
            lastHit.put(from.getUniqueId(), Bukkit.getCurrentTick());
        }
        if (ev.getDamager() instanceof Projectile p) {     // a cancelled hit lets the arrow fly on: one hit per arrow
            p.remove();
        }
        harm(victim, t, a, fort != null ? ev.getDamager() : from);     // a unit does not attack back at a building
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
    private void harm(LivingEntity victim, Stats t, Stats a, Entity from) {
        alerts.hit(victim, false, from);                  // before the hit: a unit that dies of it is attacked too
        fight(victim);
        fight(from);
        victim.playHurtAnimation(0);
        victim.setHealth(Math.max(0, victim.getHealth() - a.damage(t)));     // 0 kills it
        nameLine(victim);
        if (victim.getHealth() > 0 && from instanceof LivingEntity attacker) {
            attackBack(victim, attacker, t);
        }
    }

    // The AoE2 default stance (#733): a military unit without an order and without a target attacks its attacker.
    // A mounted unit: the horse has the order, the rider the target (#710).
    private void attackBack(LivingEntity victim, LivingEntity attacker, Stats t) {
        if (victim instanceof Mob mob && idle(mob, t) && !sameTeam(mob, attacker)
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
        return t != null && !t.classes().isEmpty() && t.attack() > 0 && !orders.containsKey(mob.getUniqueId())
                && (fighter.getTarget() == null || !fighter.getTarget().isValid()) && !stance(mob).equals("no_attack");
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
        return s == null ? "aggressive" : s;
    }

    // The blocks to an enemy that a unit attacks without an order: no limit, with stand ground its range (#1104).
    private double stanceRange(Mob mob) {
        if (!stance(mob).equals("stand_ground")) {
            return Double.MAX_VALUE;
        }
        Mob fighter = rider(mob) != null ? rider(mob) : mob;
        Range r = ranges.get(fighter.getUniqueId());
        return r != null ? r.blocks() : MELEE;
    }

    private void engage(Mob mob, LivingEntity enemy) {
        Mob fighter = rider(mob) != null ? rider(mob) : mob;
        if (fighter != mob) {
            unit(mob).getPathfinder().stopPathfinding();
        }
        reach(fighter, enemy.getLocation());
        unit(fighter).setTarget(enemy);
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
            LivingEntity t = f.getTarget();
            if (t != null && t.isValid() && !t.isDead()
                    && f.getLocation().distanceSquared(t.getLocation()) <= Math.pow(stanceRange(mob), 2)) {
                return false;
            }
            f.setTarget(null);
            f.getPathfinder().stopPathfinding();
            return true;
        });
        posts.entrySet().removeIf(en -> {      // defensive (#1105): back to the place past the chase distance
            if (!(Bukkit.getEntity(en.getKey()) instanceof Mob mob) || !mob.isValid() || orders.containsKey(en.getKey())) {
                return true;
            }
            Mob f = rider(mob) != null ? rider(mob) : mob;
            Range r = ranges.get(f.getUniqueId());
            LivingEntity t = f.getTarget();
            if (t != null && t.isValid() && !t.isDead() && mob.getLocation().distanceSquared(en.getValue())
                    <= Math.pow((r != null ? r.blocks() : MELEE) + CHASE, 2)) {
                return false;
            }
            f.setTarget(null);
            f.getPathfinder().stopPathfinding();
            reach(mob, en.getValue());
            mob.getPathfinder().moveTo(en.getValue(), 1.0);
            orders.put(mob.getUniqueId(), new Order(en.getValue(), 1.0));
            return true;
        });
    }

    // Each second: an idle unit with a line of sight attacks the nearest unit of another team in it (#775). Only
    // units with AoE2 values are enemies: Gaia animals, players and building targets are not.
    private void watch() {
        sights.entrySet().removeIf(en -> {
            Entity e = Bukkit.getEntity(en.getKey());
            if (e == null || !e.isValid()) {
                return e == null || e.isDead();                       // an unloaded unit keeps its sight
            }
            if (!(e instanceof Mob mob) || !idle(mob, stats.get(mob.getUniqueId()))) {
                return false;
            }
            double r = Math.min(en.getValue(), stanceRange(mob));
            LivingEntity best = null;
            double bestD = r * r;
            for (Entity o : mob.getNearbyEntities(r, r, r)) {
                if (o instanceof LivingEntity le && le.isValid() && stats.containsKey(le.getUniqueId())
                        && !buildings.containsKey(le.getUniqueId()) && !sameTeam(mob, le)
                        && le.getVehicle() == null && mob.getLocation().distanceSquared(le.getLocation()) <= bestD) {
                    best = le;
                    bestD = mob.getLocation().distanceSquared(le.getLocation());
                }
            }
            if (best != null) {
                engage(mob, best);
            }
            return false;
        });
    }

    @EventHandler
    public void onDeath(EntityDeathEvent ev) {               // the rider dies with its horse, else it stays (#732)
        stances.remove(ev.getEntity().getUniqueId());
        if (stats.containsKey(ev.getEntity().getUniqueId())) {
            for (Entity p : ev.getEntity().getPassengers()) {
                if (p instanceof LivingEntity r && stats.containsKey(r.getUniqueId())) {
                    r.setHealth(0);
                }
            }
        }
    }

    @EventHandler(ignoreCancelled = true)
    public void onHurt(EntityDamageEvent ev) {               // suffocation in its walls, fire, fall ...
        Entity e = ev.getEntity();
        if (!(ev instanceof EntityDamageByEntityEvent) && buildings.containsKey(e.getUniqueId())) {
            ev.setCancelled(true);
        } else if (names.containsKey(e.getUniqueId())) {      // the new health is set after the event
            Bukkit.getScheduler().runTask(this, () -> nameLine(e));
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

    private void hit(Entity target, Building b, int damage) {
        var score = hp().getScoreFor(target);
        score.setScore(Math.max(0, score.getScore() - damage));
        if (target instanceof LivingEntity le) {
            le.playHurtAnimation(0);
        }
        nameLine(target);
        if (score.getScore() == 0) {                          // the building falls
            buildings.remove(target.getUniqueId());
            names.remove(target.getUniqueId());
            score.resetScore();
            target.remove();
            Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "fill " + b.box + " minecraft:air");
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
            boolean burning = score.isScoreSet() && score.getScore() * 2 < b.max;
            if (!burning) {
                t.removeScoreboardTag("aoe2mc.burning");
                continue;
            }
            t.addScoreboardTag("aoe2mc.burning");
            var rnd = ThreadLocalRandom.current();
            int fires = 1 + (int) (3 * (1 - 2.0 * score.getScore() / b.max));   // 1 fire at half, 4 near 0
            for (int i = 0; i < fires; i++) {
                int x = rnd.nextInt(b.b[0], b.b[3] + 1), z = rnd.nextInt(b.b[2], b.b[5] + 1);
                var top = roof(t, x, z);
                if (top == null) {
                    continue;
                }
                var loc = top.getLocation().add(0.5, 1.1, 0.5);
                t.getWorld().spawnParticle(Particle.FLAME, loc, 6, 0.3, 0.2, 0.3, 0.01);
                t.getWorld().spawnParticle(Particle.LARGE_SMOKE, loc.add(0, 0.5, 0), 4, 0.3, 0.4, 0.3, 0.02);
            }
        }
    }

    /** The name and the hearts of the hit points; visible only when hurt or selected (#661). The first call keeps the
     *  custom name of the converter (the unit name in the player color) as the name. */
    private void nameLine(Entity e) {
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
        le.customName(Component.text().append(name).append(Component.text(" "))
                .append(Component.text("❤".repeat(full), NamedTextColor.RED))
                .append(Component.text("❤".repeat(HEARTS - full), NamedTextColor.DARK_GRAY)).build());
        le.setCustomNameVisible(hp < max || le.getScoreboardTags().contains("aoe2mc.selected"));
    }

    private boolean ready(Entity unit, Stats a) {
        return Bukkit.getCurrentTick() - lastHit.getOrDefault(unit.getUniqueId(), -1000) >= a.reload;
    }

    // Each tick: a melee unit next to its target hits when its reload is over. The vanilla melee goal hits each 20
    // ticks and only a living target (a building target is a slime): onHit drops its hits before the reload (#848).
    private void siege() {
        int now = Bukkit.getCurrentTick();
        lastHit.values().removeIf(t -> now - t > 400);
        for (UUID id : List.copyOf(stats.keySet())) {
            if (Bukkit.getEntity(id) instanceof Mob mob && !stats.get(id).ranged && mob.getTarget() instanceof LivingEntity t
                    && t.isValid() && (buildings.containsKey(t.getUniqueId()) || stats.containsKey(t.getUniqueId()))
                    && ready(mob, stats.get(id)) && mob.getBoundingBox().expand(REACH, 0, REACH).overlaps(t.getBoundingBox())) {
                mob.swingMainHand();
                mob.attack(t);
            }
        }
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

    private void follow() {
        orders.entrySet().removeIf(e -> {
            Entity ent = Bukkit.getEntity(e.getKey());
            if (!(ent instanceof Mob mob) || !mob.isValid()) {
                return true;
            }
            Order o = e.getValue();
            if (mob.getLocation().distanceSquared(o.goal) < 1.5 * 1.5) {
                if (mob instanceof Villager         // its brain has no goals to drop: it strolls away (#438)
                        || mob.getScoreboardTags().contains(CARRIER)) {   // its minecart pushes it on (#836)
                    mob.setAI(false);               // so it stands still until the next order
                } else if (center(mob) >= 1) {      // steer() skips path points: Minecraft walks back to them (#1078)
                    mob.getPathfinder().stopPathfinding();
                }
                return true;                                          // arrived
            }
            var pf = mob.getPathfinder();
            var path = pf.getCurrentPath();
            if (path == null || path.getFinalPoint() == null
                    || path.getFinalPoint().distanceSquared(o.goal) > 1.5 * 1.5) {
                boolean found = pf.moveTo(o.goal, o.speed);
                Location end = pf.getCurrentPath() == null ? null : pf.getCurrentPath().getFinalPoint();
                double c = center(mob);
                // a part of a path that ends at the mob leads nowhere: a builder of a dock stood still with its order
                // for a minute (#889). Drop such an order after 1 s.
                boolean stays = found && end != null && end.clone().add(c, 0, c).distanceSquared(mob.getLocation()) <= 1.5 * 1.5;
                if (found && !stays || (o.fails += stays ? 5 : 1) < 50) {
                    return false;
                }
                if (mob instanceof Villager) {          // no path for 5 s: drop the order, and stop the brain (#811)
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
                var pf = mob.getPathfinder();
                if (pf.getCurrentPath() == null && Bukkit.getCurrentTick() - o.start < 4) {
                    pf.moveTo(o.goal, o.speed);         // a unit without AI finds its path a tick later: try each tick
                }
                var path = pf.getCurrentPath();
                if (path != null) {
                    steer(mob, path, o.speed);
                    glide(mob, path, o.speed);
                }
            }
        }
    }

    // The path of a mob goes up and down a slope in L steps: a fast horse swung from side to side, stepped up onto the
    // corner of a block and fell back (#1022), an eagle scout walked up at 56 % of its speed (#851). On the ground it
    // aims at the last path point up to LOOK blocks ahead of the point next to it, whose points between are at most OFF
    // blocks off the line. Each tick the input of the mob (Minecraft MoveControl) pushes toward its next point n with
    // step x (1 - GROUND): the velocity takes that push away again.
    private static void steer(Mob mob, Pathfinder.PathResult path, double speed) {
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
        if (d < 0.05) {
            return;
        }
        double w = Math.min(step, d);
        mob.setVelocity(new Vector(dx / d * w - (e < 0.01 ? 0 : nx / e * push), mob.getVelocity().getY(),
                dz / d * w - (e < 0.01 ? 0 : nz / e * push)));
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

    /** The entity that walks for e: the carrier of a siege unit, else e. */
    private static Entity walker(Entity e) {
        return e instanceof Minecart cart && carrier(cart, false) != null ? carrier(cart, false) : e;
    }

    private Mob unit(Entity e) {
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
        Range r = ranges.get(mob.getUniqueId());
        if (r == null && mob.getScoreboardTags().contains(CARRIER) && !mob.getPassengers().isEmpty()) {
            r = ranges.get(mob.getPassengers().get(0).getUniqueId());      // the range of its siege unit (#1050)
        }
        var goals = Bukkit.getMobGoals();
        if (r != null && (mob instanceof RangedEntity || r.siege)) {
            for (var g : goals.getAllGoals(mob)) {
                if (SHOTS.contains(g.getKey().getNamespacedKey().getKey())) {
                    goals.removeGoal(mob, g.getKey());
                }
            }
            if (!goals.hasGoal(mob, rangeKey)) {
                goals.addGoal(mob, 4, new RangeGoal(mob, r));          // the priority of the vanilla bow goal
            }
        }
        return mob;
    }

    // The goals that a unit keeps: swim, and attack the target of an order. The keys of the other goals (26.3):
    // nearest_attackable and hurt_by choose targets, random_stroll, look_at_player, panic, tempt, breed, flee_sun ...
    private static final Set<String> KEEP = Set.of("float", "melee_attack", "zombie_attack", "skeleton_melee",
            "spear_use", "ranged_attack", "ranged_bow_attack", "ranged_crossbow_attack", "aoe_range");

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

    private static boolean sameTeam(Entity a, Entity b) {
        String s = side(a);
        return s != null && s.equals(side(b));
    }

    // The team name, else the player tag aoe2mc.pN: the pulse of the datapack puts a unit in its team only when its
    // chunk is loaded, and two units without a team are not enemies (#986: idle soldiers killed their neighbours).
    static String side(Entity e) {
        Team t = Bukkit.getScoreboardManager().getMainScoreboard().getEntityTeam(e);
        if (t != null) {
            return t.getName();
        }
        for (String tag : e.getScoreboardTags()) {
            if (tag.matches("aoe2mc\\.p\\d+")) {
                return tag.substring(7);
            }
        }
        return null;
    }

    private static List<Entity> select(CommandSender sender, String selector) {
        try {
            return Bukkit.selectEntities(sender, selector);
        } catch (IllegalArgumentException e) {
            return List.of();
        }
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (args.length >= 2 && args[0].startsWith("ghost")) {          // the ghost of a building (#794)
            return ghost.command(sender, args, players(sender, args[1]));
        }
        if (args.length == 3 && args[0].equals("arrows")) {            // a garrison adds arrows (#1113)
            try {
                arrows.put(UUID.fromString(args[1]), Math.max(0, Integer.parseInt(args[2])));
            } catch (IllegalArgumentException e) {                    // also NumberFormatException
                sender.sendMessage("Bad value: " + e.getMessage());
                return true;
            }
            sender.sendMessage("Arrows: " + args[2]);
            return true;
        }
        if (args.length == 2 && args[0].equals("cheats")) {
            return cheats.command(sender, args);
        }
        if (args.length == 2 && args[0].equals("deathmarks")) {        // the marks of the live replay (#846)
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
        if ((args.length == 2 || args.length == 4) && args[0].equals("minimap")) {   // live units on map 0 (#1237)
            return minimap.command(sender, args);
        }
        if (args.length >= 2 && args[0].startsWith("box")) {            // the border of the selection box (#795)
            return border.command(sender, args, players(sender, args[1]));
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
                reach(mob, goal);
                mob.setTarget(null);
                if (rider(mob) != null) {
                    rider(mob).setTarget(null);
                }
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
                if (e instanceof Mob mob) {
                    held.remove(mob.getUniqueId());
                    posts.remove(mob.getUniqueId());
                    if (args[2].equals("aggressive")) {
                        stances.remove(mob.getUniqueId());
                    } else {
                        stances.put(mob.getUniqueId(), args[2]);
                    }
                    n++;
                }
            }
            sender.sendMessage("Stance: " + n + " units");
            return true;
        }
        if ((args.length == 9 || args.length == 10) && args[0].equals("stats")) {
            double hp;
            Stats st;
            try {
                hp = Double.parseDouble(args[2]);
                st = new Stats(Integer.parseInt(args[3]), Integer.parseInt(args[4]), Integer.parseInt(args[5]),
                        !args[6].equals("0"), args[6].equals("1"), args[7].equals("-") ? Set.of() : Set.of(args[7].split(",")),
                        bonus(args[8]), args.length == 10 ? Integer.parseInt(args[9]) : 20);
            } catch (RuntimeException e) {                 // a bad number or a bonus without ":"
                sender.sendMessage("Bad value: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                Entity t = e instanceof Minecart && !e.getPassengers().isEmpty() ? e.getPassengers().get(0) : e;
                if (t instanceof LivingEntity le) {                // a siege unit: its crew takes the hits (#836)
                    AttributeInstance max = le.getAttribute(Attribute.MAX_HEALTH);
                    if (max != null) {                     // keep the lost hit points, as AoE2 does for Bloodlines (#940)
                        double lost = Math.max(0, max.getValue() - le.getHealth());
                        max.setBaseValue(hp);
                        le.setHealth(Math.min(max.getValue(), Math.max(Math.min(1, hp), hp - lost)));
                    }
                    stats.put(le.getUniqueId(), st);
                    nameLine(le);
                    Mob r = rider(le);
                    if (r != null) {
                        stats.put(r.getUniqueId(), st);          // its hits take the AoE2 attack (#710)
                    }
                    n++;
                }
            }
            sender.sendMessage("Stats: " + n + " units");
            return true;
        }
        if ((args.length == 4 || args.length == 5) && args[0].equals("range")) {
            Range r;
            try {
                r = new Range(Double.parseDouble(args[2]), Integer.parseInt(args[3]),
                        args.length == 5 ? Double.parseDouble(args[4]) : 0, args.length == 5);
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (rider(e) instanceof RangedEntity) {
                    e = rider(e);                                // a mounted archer: the rider shoots (#710)
                }
                if (e instanceof Minecart cart && r.siege) {
                    ranges.put(cart.getUniqueId(), r);           // its carrier shoots (unit())
                    Mob c = carrier(cart, false);
                    if (c != null) {
                        Bukkit.getMobGoals().removeGoal(c, rangeKey);
                    }
                    n++;
                } else if (e instanceof Mob mob && (mob instanceof RangedEntity || r.siege)) {
                    ranges.put(mob.getUniqueId(), r);
                    Bukkit.getMobGoals().removeGoal(mob, rangeKey);    // the next order adds it with the new range
                    n++;
                }
            }
            sender.sendMessage("Range: " + n + " units");
            return true;
        }
        if (args.length == 3 && args[0].equals("sight")) {
            double r;
            try {
                r = Double.parseDouble(args[2]);
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (e instanceof Mob mob && stats.containsKey(mob.getUniqueId())) {
                    sights.put(mob.getUniqueId(), r);
                    n++;
                }
            }
            sender.sendMessage("Sight: " + n + " units");
            return true;
        }
        if ((args.length == 11 || args.length == 14) && args[0].equals("building")) {
            int hp;
            double range = 0;
            Stats st;
            String box;
            int[] b = new int[6];
            try {
                hp = Integer.parseInt(args[2]);
                boolean shoots = args.length == 14;          // attack, range in blocks, reload in ticks (#1111)
                st = new Stats(shoots ? Integer.parseInt(args[11]) : 0, Integer.parseInt(args[3]),
                        Integer.parseInt(args[4]), shoots, true, Set.of("building"), Map.of(),
                        shoots ? Integer.parseInt(args[13]) : 0);
                range = shoots ? Double.parseDouble(args[12]) : 0;
                var c = new ArrayList<String>();
                for (int i = 5; i < 11; i++) {
                    b[i - 5] = Integer.parseInt(args[i]);
                    c.add(Integer.toString(b[i - 5]));
                }
                box = String.join(" ", c);
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (e instanceof LivingEntity le) {
                    le.setCollidable(false);                  // units walk up to the walls, not off the slime
                    buildings.put(le.getUniqueId(), new Building(st, box, hp, b, range));
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
                    posts.remove(mob.getUniqueId());
                    mob.getPathfinder().stopPathfinding();
                    mob.setAI(false);
                    if (rider(mob) != null) {
                        rider(mob).setTarget(null);
                    }
                    n++;
                }
            }
            sender.sendMessage("Stopped " + n + " units");
            return true;
        }
        if (args.length >= 3 && args[0].equals("menu")) {
            return menu(sender, args);
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
                parts.add(String.format(java.util.Locale.ROOT, "%s %.2f %.2f %.2f %d %d", e.getUniqueId(), l.getX(),
                        l.getY(), l.getZ(), orders.containsKey(e.getUniqueId()) ? 1 : 0,
                        fought.remove(e.getUniqueId()) | (e instanceof Mob mob && mob.getTarget() != null) ? 1 : 0));
            }
            sender.sendMessage("Where " + found.size() + ": " + String.join(", ", parts));
            return true;
        }
        if (args.length >= 2 && args[0].equals("label")) {
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (args.length > 2) {                       // a new name keeps the player color of the old one (#941)
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
        if (args.length == 4 && args[0].equals("lore")) {
            HELP.put(args[1] + ":" + text(args[2]), text(args[3]));
            sender.sendMessage("Lore: " + HELP.size() + " items");
            return true;
        }
        if (args.length == 3 && args[0].equals("attack")) {
            List<Entity> targets = select(sender, args[2]);
            if (targets.isEmpty() || !(targets.get(0) instanceof LivingEntity target)) {
                sender.sendMessage("No target");
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                Mob mob = unit(e);
                if (mob != null && mob != target && !sameTeam(mob, target)) {
                    orders.remove(mob.getUniqueId());
                    posts.remove(mob.getUniqueId());            // an order: a defensive unit chases to the end
                    Mob r = rider(mob);
                    if (r != null) {                             // the horse has no attack goal: the rider leads
                        mob.setTarget(null);
                        mob.getPathfinder().stopPathfinding();
                        mob = unit(r);
                    }
                    reach(mob, target.getLocation());
                    mob.setTarget(target);
                    held.remove(mob.getUniqueId());             // an order: the unit walks, also with stand ground
                    n++;
                }
            }
            sender.sendMessage("Attack: " + n + " units");
            return true;
        }
        return false;
    }
}
