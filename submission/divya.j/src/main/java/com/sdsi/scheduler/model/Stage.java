package com.sdsi.scheduler.model;

import java.util.Collections;
import java.util.List;

/**
 * Represents a parallel execution stage with at most N concurrent jobs (Milestone 3).
 */
public class Stage {

    private final int stageNumber;
    private final List<String> jobIds;
    private final long stageDuration;

    public Stage(int stageNumber, List<String> jobIds, long stageDuration) {
        this.stageNumber = stageNumber;
        this.jobIds = jobIds != null ? Collections.unmodifiableList(jobIds) : Collections.emptyList();
        this.stageDuration = stageDuration;
    }

    public int getStageNumber() {
        return stageNumber;
    }

    public List<String> getJobIds() {
        return jobIds;
    }

    public long getStageDuration() {
        return stageDuration;
    }

    public int getWorkerCount() {
        return jobIds.size();
    }

    @Override
    public String toString() {
        return "Stage " + stageNumber + " [Workers: " + jobIds.size() + ", Duration: " + stageDuration + "s]: " + jobIds;
    }
}
