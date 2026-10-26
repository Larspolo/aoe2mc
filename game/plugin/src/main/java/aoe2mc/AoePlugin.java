package aoe2mc;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Mob;
import org.bukkit.entity.Projectile;
import org.bukkit.entity.Villager;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scoreboard.Scoreboard;
import org.bukkit.scoreboard.Team;

/**
 * Orders for the units of the game program, with Minecraft path finding (#435). Vanilla has no command for
 * "walk to this point", so this plugin gives one to RCON:
 *   aoe moveto <selector> <x> <y> <z> [speed]   walk on the path of Mob#getPathfinder
 *   aoe attack <selector> <target selector>    Mob#setTarget: the mob attacks with its own AI
 *   aoe goals <selector>                       the goals of the first unit (#436), for checks
 *   aoe stats <selector> <hp> <attack> <melee armor> <pierce armor> <ranged 0|1> <classes|-> <class:bonus,...|->
 *                                              the AoE2 values of a unit (#514, game/combat.py stats_command)
 * Converted units have no AI (NoAI): an order turns it on. Such a unit finds no path before its first AI tick
 * (it is not "on the ground" yet), and vanilla goals (a random stroll) can take the navigation of a walking unit:
 * so the order sends the path again every 10 ticks, until the unit arrives or 10 tries found no path.
 * The path search reaches only about the follow range of the mob (16 blocks for a cow): an order raises the
 * attribute follow_range to twice the distance + 32, at most 128. Longer ways need waypoints.
 * With the AI on, a unit keeps only the goals that fit AoE2 (#436): its attack goals and "float" (it swims).
 * Wandering, looking around, panic, the choice of its own targets (a zombie attacks each villager), despawning and
 * the burning in the sun go. So a unit stands still without an order and attacks only the target of an order,
 * and an attack order skips the units of the team of the target (scoreboard teams of the datapack, #358).
 * A villager walks with its brain, not with goals: it gets NoAI when it arrives, else it strolls away (#438).
 * A hit of a unit with AoE2 values on another one takes the AoE2 damage (#514, combat.damage): max(1, attack - armor
 * + bonus). The plugin cancels the vanilla damage and sets the health: so vanilla armor items, enchantments, effects,
 * difficulty and knockback (AoE2 has none) do not change it. Max health is the attribute max_health.
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

    @Override
    public void onEnable() {
        Bukkit.getScheduler().runTaskTimer(this, this::follow, 10L, 10L);
        Bukkit.getPluginManager().registerEvents(this, this);
    }

    @EventHandler(ignoreCancelled = true)
    public void onHit(EntityDamageByEntityEvent ev) {
        Entity from = ev.getDamager();
        if (from instanceof Projectile p && p.getShooter() instanceof Entity shooter) {
            from = shooter;
        }
        Stats a = stats.get(from.getUniqueId()), t = stats.get(ev.getEntity().getUniqueId());
        if (a == null || t == null || !(ev.getEntity() instanceof LivingEntity victim)) {
            return;
        }
        ev.setCancelled(true);
        victim.playHurtAnimation(0);
        victim.setHealth(Math.max(0, victim.getHealth() - a.damage(t)));     // 0 kills it
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
                return !pf.moveTo(o.goal, o.speed) && ++o.fails >= 10;   // no path 10 times: drop the order
            }
            return false;
        });
    }

    private static Mob unit(Entity e) {
        if (!(e instanceof Mob mob)) {
            return null;
        }
        if (!mob.hasAI()) {
            mob.setAI(true);
        }
        tame(mob);                  // each order: tame() only after setAI() missed the goals of some units (#436)
        return mob;
    }

    // The goals that a unit keeps: swim, and attack the target of an order. The keys of the other goals (26.3):
    // nearest_attackable and hurt_by choose targets, random_stroll, look_at_player, panic, tempt, breed, flee_sun ...
    private static final Set<String> KEEP = Set.of("float", "melee_attack", "zombie_attack", "skeleton_melee",
            "spear_use", "ranged_attack", "ranged_bow_attack", "ranged_crossbow_attack");

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
                AttributeInstance range = mob.getAttribute(Attribute.FOLLOW_RANGE);
                if (range != null) {
                    double need = Math.min(128, 2 * mob.getLocation().distance(goal) + 32);
                    range.setBaseValue(Math.max(range.getBaseValue(), need));
                }
                mob.setTarget(null);
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
                    n++;
                }
            }
            sender.sendMessage("Stats: " + n + " units");
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
