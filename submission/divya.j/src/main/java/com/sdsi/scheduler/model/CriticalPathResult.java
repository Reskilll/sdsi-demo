package com.sdsi.scheduler.model;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Result of Critical Path Method (CPM) calculation (Milestone 4).
 */
public class CriticalPathResult {

    private final List<String> criticalPath;
    private final long minimumTotalCompletionTime;
    private final Map<String, Long> earlyStartTimes;
    private final Map<String, Long> earlyFinishTimes;
    private final Map<String, Long> latestStartTimes;
    private final Map<String, Long> latestFinishTimes;
    private final Map<String, Long> slackTimes;

    public CriticalPathResult(
            List<String> criticalPath,
            long minimumTotalCompletionTime,
            Map<String, Long> earlyStartTimes,
            Map<String, Long> earlyFinishTimes,
            Map<String, Long> latestStartTimes,
            Map<String, Long> latestFinishTimes,
            Map<String, Long> slackTimes
    ) {
        this.criticalPath = criticalPath != null ? Collections.unmodifiableList(criticalPath) : Collections.emptyList();
        this.minimumTotalCompletionTime = minimumTotalCompletionTime;
        this.earlyStartTimes = earlyStartTimes != null ? Collections.unmodifiableMap(earlyStartTimes) : Collections.emptyMap();
        this.earlyFinishTimes = earlyFinishTimes != null ? Collections.unmodifiableMap(earlyFinishTimes) : Collections.emptyMap();
        this.latestStartTimes = latestStartTimes != null ? Collections.unmodifiableMap(latestStartTimes) : Collections.emptyMap();
        this.latestFinishTimes = latestFinishTimes != null ? Collections.unmodifiableMap(latestFinishTimes) : Collections.emptyMap();
        this.slackTimes = slackTimes != null ? Collections.unmodifiableMap(slackTimes) : Collections.emptyMap();
    }

    public List<String> getCriticalPath() {
        return criticalPath;
    }

    public long getMinimumTotalCompletionTime() {
        return minimumTotalCompletionTime;
    }

    public Map<String, Long> getEarlyStartTimes() {
        return earlyStartTimes;
    }

    public Map<String, Long> getEarlyFinishTimes() {
        return earlyFinishTimes;
    }

    public Map<String, Long> getLatestStartTimes() {
        return latestStartTimes;
    }

    public Map<String, Long> getLatestFinishTimes() {
        return latestFinishTimes;
    }

    public Map<String, Long> getSlackTimes() {
        return slackTimes;
    }

    @Override
    public String toString() {
        return "Critical Path: " + String.join(" -> ", criticalPath) +
                "\nMinimum Total Completion Time: " + minimumTotalCompletionTime + " time units";
    }
}
