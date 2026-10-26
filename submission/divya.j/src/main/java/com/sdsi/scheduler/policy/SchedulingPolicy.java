package com.sdsi.scheduler.policy;

import com.sdsi.scheduler.model.JobGraph;

import java.util.Comparator;

/**
 * Strategy interface defining priority ordering for ready jobs in the scheduler.
 */
public interface SchedulingPolicy {

    /**
     * Policy display name.
     */
    String getName();

    /**
     * Constructs a deterministic comparator to order eligible job IDs in the ready queue.
     *
     * @param graph The underlying job graph
     * @return Comparator prioritizing jobs for dispatch
     */
    Comparator<String> createComparator(JobGraph graph);
}
