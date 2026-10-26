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

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Mob;
import org.bukkit.entity.Player;
import org.bukkit.entity.Projectile;
import org.bukkit.entity.Villager;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
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

import com.destroystokyo.paper.entity.RangedEntity;
import com.destroystokyo.paper.entity.ai.Goal;
import com.destroystokyo.paper.entity.ai.GoalKey;
import com.destroystokyo.paper.entity.ai.GoalType;

import net.kyori.adventure.text.Component;

/**
 * Orders for the units of the game program, with Minecraft path finding (#435). Vanilla has no command for
 * "walk to this point", so this plugin gives one to RCON:
 *   aoe moveto <selector> <x> <y> <z> [speed]   walk on the path of Mob#getPathfinder
 *   aoe attack <selector> <target selector>    Mob#setTarget: the mob attacks with its own AI
 *   aoe goals <selector>                       the goals of the first unit (#436), for checks
 *   aoe stats <selector> <hp> <attack> <melee armor> <pierce armor> <ranged 0|1> <classes|-> <class:bonus,...|->
 *                                              the AoE2 values of a unit (#514, game/combat.py stats_command)
 *   aoe range <selector> <blocks> <ticks>      a ranged unit shoots from this range, one shot per ticks (#515)
 *   aoe building <selector> <hp> <melee armor> <pierce armor> <x0> <y0> <z0> <x1> <y1> <z1>
 *                                              make the entity the target of a building (#517, combat.building)
 *   aoe menu <player> <title> <slot>:<material>:<name>:<lore> ...
 *                                              open a chest menu (#619, game/menu.py; the texts are URL-encoded)
 *   aoe menu-close <player>                    close the menu of the player
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
 * A ranged unit (#515) gets the goal "aoe_range" in place of the vanilla bow, crossbow and trident goals: their
 * range and interval are fixed in the goal objects, and the API cannot set them (no NMS in the plugin). It walks
 * on a Minecraft path to the target until the target is in range and in sight, stops, and shoots with the vanilla
 * shot of the mob (RangedEntity#rangedAttack: the arrow of a skeleton, the trident of a drowned).
 * A building is blocks, and a mob attacks only a living entity: an invisible mob without AI (a slime of the size of
 * the footprint, game/combat.py building) stands in the building and takes the attacks, so that the vanilla attack
 * goals and paths work (#517). The plugin keeps the hit points of the building (a building has more than the
 * 1024 of max_health) in the scoreboard aoe_hp, cancels all other damage to it and from it (no suffocation in the
 * walls, no slime touch), and at 0 removes it and fills the box of the building with air. The vanilla melee goal
 * hits only a target in sight, and the eye of the slime is in the walls: so a unit next to the slime that has it as
 * target hits it each second (Mob#attack, the vanilla hit with the swing), as a zombie hits.
 * Vanilla has no clickable item menu: "aoe menu" opens an inventory with the items (#619). A click on an item is
 * cancelled (the player takes nothing) and sets the score aoe_menu of the player to slot + 1 (a shift click: -(slot + 1),
 * #620); the menu stays open, so the player can click again. "aoe menu" on an open menu of the same title and size only changes the items.
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

    private record Building(Stats stats, String box) {}

    private final Map<UUID, Building> buildings = new HashMap<>();
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
            boolean near = mob.getLocation().distanceSquared(t.getLocation()) <= range.blocks * range.blocks
                    && mob.hasLineOfSight(t);
            if (near) {
                mob.getPathfinder().stopPathfinding();
            } else if (!mob.getPathfinder().hasPath() || ++ticks % 10 == 0) {     // the target can move
                reach(mob, t.getLocation());
                mob.getPathfinder().moveTo(t);
            }
            mob.lookAt(t);
            int now = Bukkit.getCurrentTick();
            if (now >= next && near && mob instanceof RangedEntity r) {
                r.rangedAttack(t, 1.0f);
                next = now + range.ticks;
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

    /** The item of "slot:material:name:lore" (lore lines split by a new line), or null for a bad slot or material. */
    static Map.Entry<Integer, ItemStack> item(String spec) {
        String[] p = spec.split(":", -1);
        Material m = p.length >= 3 ? Material.matchMaterial(p[1]) : null;
        int slot;
        try {
            slot = Integer.parseInt(p[0]);
        } catch (NumberFormatException e) {
            return null;
        }
        if (m == null || !m.isItem() || m.isAir() || slot < 0 || slot >= 54) {
            return null;
        }
        ItemStack it = new ItemStack(m);
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
        Bukkit.getScheduler().runTaskTimer(this, this::follow, 10L, 10L);
        Bukkit.getScheduler().runTaskTimer(this, this::siege, 10L, 10L);
        Bukkit.getPluginManager().registerEvents(this, this);
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
            if (a != null && b != null) {
                lastHit.put(from.getUniqueId(), Bukkit.getCurrentTick());
                hit(ev.getEntity(), b, a.damage(b.stats));
            }
            return;
        }
        if (a == null || t == null || !(ev.getEntity() instanceof LivingEntity victim)) {
            return;
        }
        ev.setCancelled(true);
        victim.playHurtAnimation(0);
        victim.setHealth(Math.max(0, victim.getHealth() - a.damage(t)));     // 0 kills it
    }

    @EventHandler(ignoreCancelled = true)
    public void onHurt(EntityDamageEvent ev) {               // suffocation in its walls, fire, fall ...
        if (!(ev instanceof EntityDamageByEntityEvent) && buildings.containsKey(ev.getEntity().getUniqueId())) {
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
        if (score.getScore() == 0) {                          // the building falls
            buildings.remove(target.getUniqueId());
            score.resetScore();
            target.remove();
            Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "fill " + b.box + " minecraft:air");
        }
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
                return !pf.moveTo(o.goal, o.speed) && ++o.fails >= 10;   // no path 10 times: drop the order
            }
            return false;
        });
    }

    // The path search reaches only about the follow range: raise it for a goal at this location.
    private static void reach(Mob mob, Location goal) {
        AttributeInstance range = mob.getAttribute(Attribute.FOLLOW_RANGE);
        if (range != null) {
            double need = Math.min(128, 2 * mob.getLocation().distance(goal) + 32);
            range.setBaseValue(Math.max(range.getBaseValue(), need));
        }
    }

    private Mob unit(Entity e) {
        if (!(e instanceof Mob mob)) {
            return null;
        }
        if (!mob.hasAI()) {
            mob.setAI(true);
        }
        tame(mob);                  // each order: tame() only after setAI() missed the goals of some units (#436)
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
                if (e instanceof Mob mob && mob instanceof RangedEntity) {
                    ranges.put(mob.getUniqueId(), r);
                    Bukkit.getMobGoals().removeGoal(mob, rangeKey);    // the next order adds it with the new range
                    n++;
                }
            }
            sender.sendMessage("Range: " + n + " units");
            return true;
        }
        if (args.length == 11 && args[0].equals("building")) {
            int hp;
            Stats st;
            String box;
            try {
                hp = Integer.parseInt(args[2]);
                st = new Stats(0, Integer.parseInt(args[3]), Integer.parseInt(args[4]), false, Set.of("building"),
                        Map.of());
                var c = new ArrayList<String>();
                for (int i = 5; i < 11; i++) {
                    c.add(Integer.toString(Integer.parseInt(args[i])));
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
                    buildings.put(le.getUniqueId(), new Building(st, box));
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
