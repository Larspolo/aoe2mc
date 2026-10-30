package aoe2mc;

import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;

/**
 * aoe frenzy &lt;selector&gt; &lt;less&gt; &lt;time&gt; &lt;min&gt;: the melee reload of the unit gets less ticks shorter for each of
 * its hits of the last time ticks, down to min ticks (the Temple Guard, #4468, game/combat.py frenzy_command).
 */
public final class Frenzy implements Ability {
    private final Map<UUID, int[]> frenzies = new HashMap<>();  // {less, time, min} in ticks
    private final Map<UUID, ArrayDeque<Integer>> hits = new HashMap<>();   // the ticks of its recent hits

    @Override
    public String name() {
        return "frenzy";
    }

    @Override
    public boolean command(AoePlugin p, CommandSender sender, String[] args) {
        if (args.length != 5) {
            return false;
        }
        int[] f = new int[3];
        try {
            for (int i = 0; i < 3; i++) {
                f[i] = Integer.parseInt(args[i + 2]);
            }
        } catch (NumberFormatException e) {
            sender.sendMessage("Bad number: " + e.getMessage());
            return true;
        }
        int n = 0;
        for (Entity e : AoePlugin.select(sender, args[1])) {
            for (Entity t : new Entity[] {AoePlugin.crew(e), e.getVehicle()}) {   // the rider and its horse (#732)
                if (t != null) {
                    frenzies.put(t.getUniqueId(), f);
                }
            }
            n++;
        }
        sender.sendMessage("Frenzy: " + n + " units");
        return true;
    }

    @Override
    public int reload(Entity unit, int reload) {
        int[] f = frenzies.get(unit.getUniqueId());
        if (f == null) {
            return reload;
        }
        int now = Bukkit.getCurrentTick();
        ArrayDeque<Integer> h = hits.getOrDefault(unit.getUniqueId(), new ArrayDeque<>());
        h.removeIf(t -> now - t >= f[1]);
        return Math.max(f[2], reload - f[0] * h.size());
    }

    @Override
    public void struck(Entity unit) {
        if (frenzies.containsKey(unit.getUniqueId())) {
            hits.computeIfAbsent(unit.getUniqueId(), k -> new ArrayDeque<>()).add(Bukkit.getCurrentTick());
        }
    }
}
