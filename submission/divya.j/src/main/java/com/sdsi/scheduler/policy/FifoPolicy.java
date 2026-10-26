package com.sdsi.scheduler.policy;

import com.sdsi.scheduler.model.JobGraph;

import java.util.Comparator;

/**
 * Deterministic FIFO (First-In, First-Out) policy.
 * When multiple jobs become ready, they are ordered deterministically by job ID.
 */
public class FifoPolicy implements SchedulingPolicy {

    @Override
    public String getName() {
        return "FIFO (Deterministic Lexicographical)";
    }

    @Override
    public Comparator<String> createComparator(JobGraph graph) {
        return Comparator.naturalOrder();
    }
}
