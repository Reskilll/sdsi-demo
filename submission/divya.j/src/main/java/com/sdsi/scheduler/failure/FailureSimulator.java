package com.sdsi.scheduler.failure;

import com.sdsi.scheduler.engine.FailurePropagator;
import com.sdsi.scheduler.model.FailureReport;
import com.sdsi.scheduler.model.JobGraph;
import com.sdsi.scheduler.sorter.TopologicalSorter;

/**
 * Milestone 5: Backward-compatible facade for FailurePropagator.
 */
public class FailureSimulator {

    private final FailurePropagator propagator;

    public FailureSimulator() {
        this.propagator = new FailurePropagator();
    }

    public FailureSimulator(TopologicalSorter sorter) {
        this.propagator = new FailurePropagator(sorter);
    }

    public FailureReport simulateFailure(JobGraph graph, String failedJobId) {
        return propagator.propagateFailure(graph, failedJobId);
    }
}
