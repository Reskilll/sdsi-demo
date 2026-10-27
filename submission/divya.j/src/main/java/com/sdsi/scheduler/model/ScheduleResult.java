package com.sdsi.scheduler.model;

import java.util.*;

/**
 * Immutable comprehensive execution report produced by the Discrete-Event Scheduler.
 */
public class ScheduleResult {

    private final int workerLimit;
    private final String schedulingPolicy;
    private final long totalMakespan;
    private final long criticalPathDuration;
    private final double workerUtilization; // 0.0 to 100.0%
    private final List<Stage> stages;
    private final List<ScheduledTask> scheduledTasks;
    private final Map<String, JobExecutionState> jobStates;
    private final List<String> executionOrder;

    public ScheduleResult(
            int workerLimit,
            String schedulingPolicy,
            long totalMakespan,
            long criticalPathDuration,
            double workerUtilization,
            List<Stage> stages,
            List<ScheduledTask> scheduledTasks,
            Map<String, JobExecutionState> jobStates,
            List<String> executionOrder
    ) {
        this.workerLimit = workerLimit;
        this.schedulingPolicy = schedulingPolicy;
        this.totalMakespan = totalMakespan;
        this.criticalPathDuration = criticalPathDuration;
        this.workerUtilization = workerUtilization;
        this.stages = stages != null ? Collections.unmodifiableList(stages) : Collections.emptyList();
        this.scheduledTasks = scheduledTasks != null ? Collections.unmodifiableList(scheduledTasks) : Collections.emptyList();
        this.jobStates = jobStates != null ? Collections.unmodifiableMap(jobStates) : Collections.emptyMap();
        this.executionOrder = executionOrder != null ? Collections.unmodifiableList(executionOrder) : Collections.emptyList();
    }

    public int getWorkerLimit() {
        return workerLimit;
    }

    public String getSchedulingPolicy() {
        return schedulingPolicy;
    }

    public long getTotalMakespan() {
        return totalMakespan;
    }

    public long getCriticalPathDuration() {
        return criticalPathDuration;
    }

    public double getWorkerUtilization() {
        return workerUtilization;
    }

    public List<Stage> getStages() {
        return stages;
    }

    public List<ScheduledTask> getScheduledTasks() {
        return scheduledTasks;
    }

    public Map<String, JobExecutionState> getJobStates() {
        return jobStates;
    }

    public List<String> getExecutionOrder() {
        return executionOrder;
    }

    public List<String> getCompletedJobs() {
        List<String> list = new ArrayList<>();
        for (JobExecutionState s : jobStates.values()) {
            if (s.getStatus() == JobStatus.COMPLETED) {
                list.add(s.getJobId());
            }
        }
        return list;
    }

    public List<String> getFailedJobs() {
        List<String> list = new ArrayList<>();
        for (JobExecutionState s : jobStates.values()) {
            if (s.getStatus() == JobStatus.FAILED) {
                list.add(s.getJobId());
            }
        }
        return list;
    }

    public List<String> getSkippedJobs() {
        List<String> list = new ArrayList<>();
        for (JobExecutionState s : jobStates.values()) {
            if (s.getStatus() == JobStatus.SKIPPED) {
                list.add(s.getJobId());
            }
        }
        return list;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("Schedule Execution Summary:\n");
        sb.append("  Workers (N)           : ").append(workerLimit).append("\n");
        sb.append("  Scheduling Policy     : ").append(schedulingPolicy).append("\n");
        sb.append("  Total Makespan        : ").append(totalMakespan).append(" time units\n");
        sb.append("  Critical Path Bound   : ").append(criticalPathDuration).append(" time units (theoretical lower bound)\n");
        sb.append(String.format("  Worker Utilization    : %.2f%%\n", workerUtilization));
        sb.append("  Total Jobs Completed  : ").append(getCompletedJobs().size()).append("\n");
        if (!getFailedJobs().isEmpty()) {
            sb.append("  Total Jobs Failed     : ").append(getFailedJobs()).append("\n");
        }
        if (!getSkippedJobs().isEmpty()) {
            sb.append("  Total Jobs Skipped    : ").append(getSkippedJobs()).append("\n");
        }
        sb.append("  Note on Optimality    : Critical-path duration represents the unconstrained parallelism lower bound.\n");
        sb.append("                          Resource-Constrained Project Scheduling (RCPSP) with worker limit N is NP-hard;\n");
        sb.append("                          heuristic dispatch rules achieve high throughput but are not guaranteed globally optimal.\n\n");
        sb.append("Timeline:\n");
        for (ScheduledTask task : scheduledTasks) {
            sb.append("  ").append(task).append("\n");
        }
        return sb.toString().trim();
    }
}
