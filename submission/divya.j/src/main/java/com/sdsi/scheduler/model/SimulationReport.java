package com.sdsi.scheduler.model;

import java.util.Collections;
import java.util.List;

/**
 * Report containing discrete-event simulation results under worker limit N.
 */
public class SimulationReport {

    private final int workerLimit;
    private final List<ScheduledTask> scheduledTasks;
    private final long totalMakespan;

    public SimulationReport(int workerLimit, List<ScheduledTask> scheduledTasks, long totalMakespan) {
        this.workerLimit = workerLimit;
        this.scheduledTasks = scheduledTasks != null ? Collections.unmodifiableList(scheduledTasks) : Collections.emptyList();
        this.totalMakespan = totalMakespan;
    }

    public int getWorkerLimit() {
        return workerLimit;
    }

    public List<ScheduledTask> getScheduledTasks() {
        return scheduledTasks;
    }

    public long getTotalMakespan() {
        return totalMakespan;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("Worker Limit: ").append(workerLimit)
          .append(" | Simulated Total Makespan: ").append(totalMakespan).append(" time units\n");
        sb.append("Timeline:\n");
        for (ScheduledTask task : scheduledTasks) {
            sb.append("  ").append(task).append("\n");
        }
        return sb.toString().trim();
    }
}
