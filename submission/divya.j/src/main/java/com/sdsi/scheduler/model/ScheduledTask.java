package com.sdsi.scheduler.model;

/**
 * Represents a job scheduled onto a worker with an explicit time window.
 */
public class ScheduledTask {

    private final String jobId;
    private final int workerId;
    private final long startTime;
    private final long endTime;
    private final long duration;

    public ScheduledTask(String jobId, int workerId, long startTime, long endTime, long duration) {
        this.jobId = jobId;
        this.workerId = workerId;
        this.startTime = startTime;
        this.endTime = endTime;
        this.duration = duration;
    }

    public String getJobId() {
        return jobId;
    }

    public int getWorkerId() {
        return workerId;
    }

    public long getStartTime() {
        return startTime;
    }

    public long getEndTime() {
        return endTime;
    }

    public long getDuration() {
        return duration;
    }

    @Override
    public String toString() {
        return String.format("[T%02d - T%02d] Worker-%d : %s (duration: %d)",
                startTime, endTime, workerId, jobId, duration);
    }
}
