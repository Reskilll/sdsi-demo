package com.sdsi.scheduler.policy;

import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;

import java.util.Comparator;

/**
 * Shortest Processing Time / Shortest Job First (SJF) policy.
 * Prioritizes jobs with smaller duration to maximize throughput and minimize average flow time.
 * Ties are broken deterministically by job ID.
 */
public class ShortestJobFirstPolicy implements SchedulingPolicy {

    @Override
    public String getName() {
        return "Shortest Job First (SJF)";
    }

    @Override
    public Comparator<String> createComparator(JobGraph graph) {
        return (id1, id2) -> {
            Job j1 = graph.getJob(id1);
            Job j2 = graph.getJob(id2);
            long d1 = j1 != null ? j1.getDuration() : 0L;
            long d2 = j2 != null ? j2.getDuration() : 0L;

            int cmp = Long.compare(d1, d2);
            if (cmp != 0) {
                return cmp;
            }
            return id1.compareTo(id2); // deterministic tie-break
        };
    }
}
