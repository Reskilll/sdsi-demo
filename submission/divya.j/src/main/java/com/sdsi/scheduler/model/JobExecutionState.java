package com.sdsi.scheduler.model;

import java.util.Objects;

/**
 * Tracks the execution state and timing metrics for a job.
 */
public class JobExecutionState {

    private final String jobId;
    private JobStatus status;
    private Integer workerId;
    private Long startTime;
    private Long finishTime;
    private String reason;

    public JobExecutionState(String jobId) {
        this.jobId = Objects.requireNonNull(jobId, "jobId cannot be null");
        this.status = JobStatus.PENDING;
    }

    public String getJobId() {
        return jobId;
    }

    public JobStatus getStatus() {
        return status;
    }

    public void setStatus(JobStatus status) {
        this.status = status;
    }

    public Integer getWorkerId() {
        return workerId;
    }

    public void setWorkerId(Integer workerId) {
        this.workerId = workerId;
    }

    public Long getStartTime() {
        return startTime;
    }

    public void setStartTime(Long startTime) {
        this.startTime = startTime;
    }

    public Long getFinishTime() {
        return finishTime;
    }

    public void setFinishTime(Long finishTime) {
        this.finishTime = finishTime;
    }

    public String getReason() {
        return reason;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }

    @Override
    public String toString() {
        return "JobExecutionState{" +
                "jobId='" + jobId + '\'' +
                ", status=" + status +
                ", workerId=" + workerId +
                ", startTime=" + startTime +
                ", finishTime=" + finishTime +
                (reason != null ? ", reason='" + reason + '\'' : "") +
                '}';
    }
}
