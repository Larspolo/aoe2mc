package aoe2mc;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;

/**
 * aoe veteran &lt;selector&gt; &lt;attack&gt; &lt;max&gt;: the unit gets attack more for each unit that it kills, up to max (the
 * Jaguar Warrior, #4467, game/combat.py veteran_command); a new call keeps the kills (an Elite upgrade).
 */
public final class Veteran implements Ability {
    private final Map<UUID, int[]> veterans = new HashMap<>();  // {attack, max, kills}; rider and horse share it

    @Override
    public String name() {
        return "veteran";
    }

    @Override
    public boolean command(AoePlugin p, CommandSender sender, String[] args) {
        if (args.length != 4) {
            return false;
        }
        int attack, max;
        try {
            attack = Integer.parseInt(args[2]);
            max = Integer.parseInt(args[3]);
        } catch (NumberFormatException e) {
            sender.sendMessage("Bad number: " + e.getMessage());
            return true;
        }
        int n = 0;
        for (Entity e : AoePlugin.select(sender, args[1])) {
            int[] v = veterans.getOrDefault(e.getUniqueId(), new int[3]);   // an Elite upgrade keeps the kills
            v[0] = attack;
            v[1] = max;
            for (Entity t : new Entity[] {AoePlugin.crew(e), e.getVehicle(), e}) {   // the rider and its horse (#732)
                if (t != null) {
                    veterans.put(t.getUniqueId(), v);
                }
            }
            n++;
        }
        sender.sendMessage("Veteran: " + n + " units");
        return true;
    }

    @Override
    public int attack(Entity e) {
        int[] v = e == null ? null : veterans.get(e.getUniqueId());
        return v == null ? 0 : Math.min(v[1], v[0] * v[2]);
    }

    @Override
    public void killed(Entity by) {
        if (veterans.get(by.getUniqueId()) instanceof int[] v) {
            v[2]++;                                            // a Jaguar Warrior gets stronger
        }
    }
}
