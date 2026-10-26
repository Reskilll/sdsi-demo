package com.sdsi.scheduler.model;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Structured report detailing failure propagation and downstream skipped tasks.
 */
public class FailureReport {

    private final String failedJobId;
    private final Set<String> directDownstreamJobs;
    private final List<String> allSkippedJobs;
    private final List<String> executableJobs;
    private final int totalJobs;
    private final Map<String, String> skipReasons;

    public FailureReport(
            String failedJobId,
            Set<String> directDownstreamJobs,
            List<String> allSkippedJobs,
            List<String> executableJobs,
            int totalJobs
    ) {
        this(failedJobId, directDownstreamJobs, allSkippedJobs, executableJobs, totalJobs, Collections.emptyMap());
    }

    public FailureReport(
            String failedJobId,
            Set<String> directDownstreamJobs,
            List<String> allSkippedJobs,
            List<String> executableJobs,
            int totalJobs,
            Map<String, String> skipReasons
    ) {
        this.failedJobId = failedJobId;
        this.directDownstreamJobs = directDownstreamJobs != null ? Collections.unmodifiableSet(directDownstreamJobs) : Collections.emptySet();
        this.allSkippedJobs = allSkippedJobs != null ? Collections.unmodifiableList(allSkippedJobs) : Collections.emptyList();
        this.executableJobs = executableJobs != null ? Collections.unmodifiableList(executableJobs) : Collections.emptyList();
        this.totalJobs = totalJobs;
        this.skipReasons = skipReasons != null ? Collections.unmodifiableMap(skipReasons) : Collections.emptyMap();
    }

    public String getFailedJobId() {
        return failedJobId;
    }

    public Set<String> getDirectDownstreamJobs() {
        return directDownstreamJobs;
    }

    public List<String> getAllSkippedJobs() {
        return allSkippedJobs;
    }

    public List<String> getExecutableJobs() {
        return executableJobs;
    }

    public int getTotalJobs() {
        return totalJobs;
    }

    public int getSkippedCount() {
        return allSkippedJobs.size();
    }

    public int getExecutableCount() {
        return executableJobs.size();
    }

    public Map<String, String> getSkipReasons() {
        return skipReasons;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("Failure Propagation Report for Job: '").append(failedJobId).append("'\n");
        sb.append("  Direct Dependents: ").append(directDownstreamJobs).append("\n");
        sb.append("  Total Skipped Jobs (").append(getSkippedCount()).append("/").append(totalJobs).append("): ").append(allSkippedJobs).append("\n");
        if (!skipReasons.isEmpty()) {
            sb.append("  Skip Details:\n");
            for (Map.Entry<String, String> entry : skipReasons.entrySet()) {
                sb.append("   - Job '").append(entry.getKey()).append("': ").append(entry.getValue()).append("\n");
            }
        }
        sb.append("  Unaffected Executable Jobs (").append(getExecutableCount()).append("/").append(totalJobs).append("): ").append(executableJobs);
        return sb.toString();
    }
}
