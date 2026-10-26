package aoe2mc;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
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
import org.bukkit.entity.Mob;
import org.bukkit.entity.Pillager;
import org.bukkit.entity.Player;
import org.bukkit.entity.Projectile;
import org.bukkit.entity.Villager;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityDeathEvent;
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
 *   aoe attack <selector> <target selector>    Mob#setTarget: the mob attacks with its own AI
 *   aoe goals <selector>                       the goals of the first unit (#436), for checks
 *   aoe stats <selector> <hp> <attack> <melee armor> <pierce armor> <ranged 0|1> <classes|-> <class:bonus,...|->
 *                                              the AoE2 values of a unit (#514, game/combat.py stats_command)
 *   aoe stop <selector>                        stop the walk and turn the AI off: the unit stands still (#437)
 *   aoe range <selector> <blocks> <ticks>      a ranged unit shoots from this range, one shot per ticks (#515)
 *   aoe sight <selector> <blocks>              an idle unit attacks an enemy in this line of sight (#775)
 *   aoe building <selector> <hp> <melee armor> <pierce armor> <x0> <y0> <z0> <x1> <y1> <z1>
 *                                              make the entity the target of a building (#517, combat.building)
 *   aoe menu <player> <title> <slot>:<material>:<name>:<lore>[:<count>] ...
 *                                              open a chest menu (#619, game/menu.py; the texts are URL-encoded)
 *   aoe menu-close <player>                    close the menu of the player
 *   aoe cheats <code>,<code>,...|-             the AoE2 cheat codes in the chat (#816, Cheats.java; URL-encoded)
 *   aoe label <selector> [name]                show the name line again (after a selection change); a name sets
 *                                              the name of a building target (#661)
 *   aoe where <selector> [from]                "Where <count>: <uuid> <x> <y> <z> <order 0|1> <target 0|1>, ..." for
 *                                              WHERE_PAGE units from index `from` in UUID order (#813, tools/replay_drift.py)
 *   aoe box <player> <x> <z> <dye>             draw the selection box from this corner to the look (#795, Border.java)
 *   aoe box-clear <player>                     end the border of the selection box
 * Converted units have no AI (NoAI): an order turns it on. Such a unit finds no path before its first AI tick
 * (it is not "on the ground" yet), and vanilla goals (a random stroll) can take the navigation of a walking unit:
 * so the order sends the path again every 2 ticks (#437: 10 ticks made each walk 0.5 s longer), until the unit
 * arrives or 50 tries (5 s) found no path.
 * The path search reaches only about the follow range of the mob (16 blocks for a cow): an order raises the
 * attribute follow_range to twice the distance + 32, at most 128. Longer ways need waypoints.
 * An order also sets the attribute step_height to 1 (as a horse): the ground of a map has many steps of one block,
 * and a jump on each made the replay units walk at 64 % of their speed (#829).
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
 * A villager walks with its brain, not with goals: it gets NoAI when it arrives, else it strolls away (#438).
 * `aoe stop` stops a walk and sets NoAI (#437: a villager without a path).
 * A hit of a unit with AoE2 values on another one takes the AoE2 damage (#514, combat.damage): max(1, attack - armor
 * + bonus). The plugin cancels the vanilla damage and sets the health: so vanilla armor items, enchantments, effects,
 * difficulty and knockback (AoE2 has none) do not change it. Max health is the attribute max_health.
 * A ranged unit (#515) gets the goal "aoe_range" in place of the vanilla bow, crossbow and trident goals: their
 * range and interval are fixed in the goal objects, and the API cannot set them (no NMS in the plugin). It walks
 * on a Minecraft path to the target until the target is in range and in sight, stops, and shoots with the vanilla
 * shot of the mob (RangedEntity#rangedAttack: the trident of a drowned), or with an aimed arrow (shoot: a skeleton or pillager).
 * A mounted unit (#710) is a horse (its UUID in aoe2mc.json) with a rider: a horse has no attack goal. The rider gets
 * the values of "aoe stats", the range of "aoe range" and the target of "aoe attack", and the horse gets AI without goals:
 * a riding mob walks with the navigation of its vehicle (vanilla Mob#getNavigation), so the horse follows the rider.
 * A hit on the rider takes the hit points of the horse, and the rider dies with the horse (#732).
 * A building is blocks, and a mob attacks only a living entity: an invisible mob without AI (a slime of the size of
 * the footprint, game/combat.py building) stands in the building and takes the attacks, so that the vanilla attack
 * goals and paths work (#517). The plugin keeps the hit points of the building (a building has more than the
 * 1024 of max_health) in the scoreboard aoe_hp, cancels all other damage to it and from it (no suffocation in the
 * walls, no slime touch), and at 0 removes it and fills the box of the building with air. The vanilla melee goal
 * hits only a target in sight, and the eye of the slime is in the walls: so a unit next to the slime that has it as
 * target hits it each second (Mob#attack, the vanilla hit with the swing), as a zombie hits. A ranged unit shoots
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
    private record Stats(int attack, int melee, int pierce, boolean ranged, Set<String> classes,
                         Map<String, Integer> bonus) {
        int damage(Stats t) {                                 // the same rule as game/combat.py damage()
            int bonus = 0;
            for (String c : t.classes) {
                bonus += this.bonus.getOrDefault(c, 0);
            }
            return Math.max(1, Math.max(0, attack - (ranged ? t.pierce : t.melee)) + bonus);
        }
    }

    private final Map<UUID, Stats> stats = new HashMap<>();
    private final Ghost ghost = new Ghost(this);
    private final Cheats cheats = new Cheats(this);
    private final Border border = new Border();

    private record Building(Stats stats, String box, int max, int[] b) {}   // b: x0 y0 z0 x1 y1 z1 of box

    private final Map<UUID, Building> buildings = new HashMap<>();
    private final Map<UUID, Component> names = new HashMap<>();      // the name in the name line (#661)
    private static final int HEARTS = 5;
    private static final int WHERE_PAGE = 40;                          // aoe where: about 3000 bytes per answer
    private final Map<UUID, Integer> lastHit = new HashMap<>();      // tick of the last hit of a unit on a building
    private static final double REACH = Math.sqrt(2.04) - 0.6;       // vanilla melee reach past the hit box

    private static final class Order {
        final Location goal;
        final double speed;
        int fails;

        Order(Location goal, double speed) {
            this.goal = goal;
            this.speed = speed;
        }
    }

    private final Map<UUID, Order> orders = new HashMap<>();

    private record Range(double blocks, int ticks) {
    }

    private final Map<UUID, Range> ranges = new HashMap<>();
    private final Map<UUID, Double> sights = new HashMap<>();       // the line of sight of a unit in blocks (#775)
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
            } else if (!mob.getPathfinder().hasPath() || ++ticks % 10 == 0) {     // the target can move
                reach(mob, t.getLocation());
                mob.getPathfinder().moveTo(t);
            }
            mob.lookAt(t);
            int now = Bukkit.getCurrentTick();
            if (now >= next && near && mob instanceof RangedEntity r) {
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
            if (p.length > 3 && !p[3].isEmpty()) {
                meta.lore(text(p[3]).lines().map(l -> (Component) Component.text(l)).toList());
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
        Bukkit.getScheduler().runTaskTimer(this, ghost::tick, 1L, 1L);
        Bukkit.getScheduler().runTaskTimer(this, border::tick, 4L, 4L);
        Bukkit.getScheduler().runTaskTimer(this, this::siege, 10L, 10L);
        Bukkit.getScheduler().runTaskTimer(this, this::burn, 20L, 20L);
        Bukkit.getScheduler().runTaskTimer(this, this::watch, 20L, 20L);
        Bukkit.getPluginManager().registerEvents(this, this);
        Bukkit.getPluginManager().registerEvents(cheats, this);
    }

    @EventHandler(ignoreCancelled = true)
    public void onHit(EntityDamageByEntityEvent ev) {
        Entity from = ev.getDamager();
        if (from instanceof Projectile p && p.getShooter() instanceof Entity shooter) {
            from = shooter;
        }
        Stats a = stats.get(from.getUniqueId()), t = stats.get(ev.getEntity().getUniqueId());
        Building b = buildings.get(ev.getEntity().getUniqueId());
        if (buildings.containsKey(from.getUniqueId()) || b != null) {
            ev.setCancelled(true);
            if (a != null && b != null && !(ev.getDamager() instanceof Projectile)) {   // RangeGoal counts a shot
                lastHit.put(from.getUniqueId(), Bukkit.getCurrentTick());
                hit(ev.getEntity(), b, a.damage(b.stats));
                hitEffect(ev.getEntity(), b, from);
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
        victim.playHurtAnimation(0);
        victim.setHealth(Math.max(0, victim.getHealth() - a.damage(t)));     // 0 kills it
        if (ev.getDamager() instanceof Projectile p) {     // a cancelled hit lets the arrow fly on: one hit per arrow
            p.remove();
        }
        nameLine(victim);
        if (victim.getHealth() > 0 && from instanceof LivingEntity attacker) {
            attackBack(victim, attacker, t);
        }
    }

    // The AoE2 default stance (#733): a military unit without an order and without a target attacks its attacker.
    // A mounted unit: the horse has the order, the rider the target (#710).
    private void attackBack(LivingEntity victim, LivingEntity attacker, Stats t) {
        if (victim instanceof Mob mob && idle(mob, t) && !sameTeam(mob, attacker)) {
            engage(mob, attacker);
        }
    }

    // A military unit without an order and without a target: the units of the AoE2 default stance (#733, #775).
    private boolean idle(Mob mob, Stats t) {
        Mob fighter = rider(mob) != null ? rider(mob) : mob;
        return t != null && !t.classes().isEmpty() && t.attack() > 0 && !orders.containsKey(mob.getUniqueId())
                && (fighter.getTarget() == null || !fighter.getTarget().isValid());
    }

    private void engage(Mob mob, LivingEntity enemy) {
        Mob fighter = rider(mob) != null ? rider(mob) : mob;
        if (fighter != mob) {
            unit(mob).getPathfinder().stopPathfinding();
        }
        reach(fighter, enemy.getLocation());
        unit(fighter).setTarget(enemy);
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
            double r = en.getValue();
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

    private void siege() {
        int now = Bukkit.getCurrentTick();
        lastHit.values().removeIf(t -> now - t > 100);
        for (UUID id : List.copyOf(stats.keySet())) {
            if (Bukkit.getEntity(id) instanceof Mob mob && !stats.get(id).ranged && mob.getTarget() instanceof LivingEntity t
                    && buildings.containsKey(t.getUniqueId()) && now - lastHit.getOrDefault(id, -100) >= 20
                    && mob.getBoundingBox().expand(REACH, 0, REACH).overlaps(t.getBoundingBox())) {
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
                if (mob instanceof Villager) {      // its brain has no goals to drop: it strolls away (#438)
                    mob.setAI(false);               // so it stands still until the next order
                }
                return true;                                          // arrived
            }
            var pf = mob.getPathfinder();
            var path = pf.getCurrentPath();
            if (path == null || path.getFinalPoint() == null
                    || path.getFinalPoint().distanceSquared(o.goal) > 1.5 * 1.5) {
                if (pf.moveTo(o.goal, o.speed) || ++o.fails < 50) {
                    return false;
                }
                if (mob instanceof Villager) {          // no path for 5 s: drop the order, and stop the brain (#811)
                    mob.setAI(false);
                }
                getLogger().info("aoe2mc: no path " + mob.getUniqueId() + " " + o.goal.getX() + " " + o.goal.getY()
                        + " " + o.goal.getZ());
                return true;
            }
            return false;
        });
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

    private Mob unit(Entity e) {
        if (!(e instanceof Mob mob)) {
            return null;
        }
        if (!mob.hasAI()) {
            mob.setAI(true);
        }
        tame(mob);                  // each order: tame() only after setAI() missed the goals of some units (#436)
        AttributeInstance step = mob.getAttribute(Attribute.STEP_HEIGHT);
        if (step != null && step.getBaseValue() < 1) {
            step.setBaseValue(1);                                      // no jump on a step of one block (#829)
        }
        Range r = ranges.get(mob.getUniqueId());
        var goals = Bukkit.getMobGoals();
        if (r != null && mob instanceof RangedEntity) {
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
        Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
        Team t = sb.getEntityTeam(a);
        return t != null && t.equals(sb.getEntityTeam(b));
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
        if (args.length == 2 && args[0].equals("cheats")) {
            return cheats.command(sender, args);
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
        if (args.length == 9 && args[0].equals("stats")) {
            double hp;
            Stats st;
            try {
                hp = Double.parseDouble(args[2]);
                st = new Stats(Integer.parseInt(args[3]), Integer.parseInt(args[4]), Integer.parseInt(args[5]),
                        args[6].equals("1"), args[7].equals("-") ? Set.of() : Set.of(args[7].split(",")),
                        bonus(args[8]));
            } catch (RuntimeException e) {                 // a bad number or a bonus without ":"
                sender.sendMessage("Bad value: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (e instanceof LivingEntity le) {
                    AttributeInstance max = le.getAttribute(Attribute.MAX_HEALTH);
                    if (max != null) {
                        max.setBaseValue(hp);
                        le.setHealth(hp);
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
        if (args.length == 4 && args[0].equals("range")) {
            Range r;
            try {
                r = new Range(Double.parseDouble(args[2]), Integer.parseInt(args[3]));
            } catch (NumberFormatException e) {
                sender.sendMessage("Bad number: " + e.getMessage());
                return true;
            }
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (rider(e) instanceof RangedEntity) {
                    e = rider(e);                                // a mounted archer: the rider shoots (#710)
                }
                if (e instanceof Mob mob && mob instanceof RangedEntity) {
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
        if (args.length == 11 && args[0].equals("building")) {
            int hp;
            Stats st;
            String box;
            int[] b = new int[6];
            try {
                hp = Integer.parseInt(args[2]);
                st = new Stats(0, Integer.parseInt(args[3]), Integer.parseInt(args[4]), false, Set.of("building"),
                        Map.of());
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
                    buildings.put(le.getUniqueId(), new Building(st, box, hp, b));
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
        if (args.length == 2 && args[0].equals("stop")) {
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (e instanceof Mob mob) {
                    orders.remove(mob.getUniqueId());
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
                        e instanceof Mob mob && mob.getTarget() != null ? 1 : 0));
            }
            sender.sendMessage("Where " + found.size() + ": " + String.join(", ", parts));
            return true;
        }
        if (args.length >= 2 && args[0].equals("label")) {
            int n = 0;
            for (Entity e : select(sender, args[1])) {
                if (args.length > 2) {
                    names.put(e.getUniqueId(), Component.text(String.join(" ", List.of(args).subList(2, args.length))));
                }
                if (names.containsKey(e.getUniqueId())) {
                    nameLine(e);
                    n++;
                }
            }
            sender.sendMessage("Label: " + n + " units");
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
                    Mob r = rider(mob);
                    if (r != null) {                             // the horse has no attack goal: the rider leads
                        mob.setTarget(null);
                        mob.getPathfinder().stopPathfinding();
                        mob = unit(r);
                    }
                    reach(mob, target.getLocation());
                    mob.setTarget(target);
                    n++;
                }
            }
            sender.sendMessage("Attack: " + n + " units");
            return true;
        }
        return false;
    }
}
