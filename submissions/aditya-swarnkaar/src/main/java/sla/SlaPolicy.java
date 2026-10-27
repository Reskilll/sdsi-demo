package sla;

import java.util.*;

/**
 * SLA policy: maps priority to target business-minutes.
 * Defaults: P1=240, P2=480, P3=1440, P4=4320.
 */
public class SlaPolicy {
    private final Map<String, Long> targets; // priority -> minutes

    public static final long DEFAULT_P1 = 4 * 60;    // 240
    public static final long DEFAULT_P2 = 8 * 60;    // 480
    public static final long DEFAULT_P3 = 24 * 60;   // 1440
    public static final long DEFAULT_P4 = 72 * 60;   // 4320

    public static final Map<String, Long> DEFAULTS = Map.of(
        "P1", DEFAULT_P1, "P2", DEFAULT_P2, "P3", DEFAULT_P3, "P4", DEFAULT_P4
    );

    public SlaPolicy(Map<String, Long> targets) {
        this.targets = Map.copyOf(targets);
    }

    /** Default policy with P1=240, P2=480, P3=1440, P4=4320. */
    public static SlaPolicy defaults() {
        return new SlaPolicy(DEFAULTS);
    }

    /** Target business-minutes for the given priority. */
    public long target(String priority) {
        return targets.getOrDefault(priority, -1L);
    }

    public Set<String> priorities() { return targets.keySet(); }
}