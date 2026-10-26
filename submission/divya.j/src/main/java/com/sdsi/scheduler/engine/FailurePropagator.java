package com.sdsi.scheduler.engine;

import com.sdsi.scheduler.model.FailureReport;
import com.sdsi.scheduler.model.JobGraph;
import com.sdsi.scheduler.sorter.TopologicalSorter;

import java.util.*;

/**
 * Milestone 5: Transitive Downstream Failure Propagation.
 * Traverses forward dependent edges using BFS to compute all skipped jobs and failure reasons.
 * Complexity: O(V + E)
 */
public class FailurePropagator {

    private final TopologicalSorter sorter;

    public FailurePropagator() {
        this(new TopologicalSorter());
    }

    public FailurePropagator(TopologicalSorter sorter) {
        this.sorter = Objects.requireNonNull(sorter, "TopologicalSorter cannot be null");
    }

    /**
     * Propagates a failure across downstream dependencies.
     *
     * @param graph Validated JobGraph
     * @param failedJobId Target failed job ID
     * @return Structured failure report
     */
    public FailureReport propagateFailure(JobGraph graph, String failedJobId) {
        if (graph == null || graph.isEmpty()) {
            throw new IllegalArgumentException("Cannot propagate failure on an empty or null graph.");
        }
        if (failedJobId == null || !graph.containsJob(failedJobId)) {
            throw new IllegalArgumentException("Unknown failure target: Job '" + failedJobId + "' does not exist in graph.");
        }

        Set<String> directDownstream = new LinkedHashSet<>(graph.getDependents(failedJobId));

        // BFS traversal along dependent edges to compute transitive closure
        Set<String> skippedSet = new HashSet<>();
        Map<String, String> skipReasons = new LinkedHashMap<>();

        Queue<String> queue = new ArrayDeque<>();
        for (String child : directDownstream) {
            skippedSet.add(child);
            skipReasons.put(child, "Direct prerequisite '" + failedJobId + "' failed");
            queue.offer(child);
        }

        while (!queue.isEmpty()) {
            String current = queue.poll();
            for (String next : graph.getDependents(current)) {
                if (skippedSet.add(next)) {
                    skipReasons.put(next, "Transitive prerequisite '" + current + "' was skipped due to failure of '" + failedJobId + "'");
                    queue.offer(next);
                }
            }
        }

        // Order according to topological sort
        List<String> topoOrder = sorter.sort(graph);
        List<String> allSkipped = new ArrayList<>(skippedSet.size());
        List<String> executable = new ArrayList<>(graph.size() - skippedSet.size() - 1);

        for (String jobId : topoOrder) {
            if (jobId.equals(failedJobId)) {
                continue; // Failed job
            }
            if (skippedSet.contains(jobId)) {
                allSkipped.add(jobId);
            } else {
                executable.add(jobId);
            }
        }

        return new FailureReport(
                failedJobId,
                directDownstream,
                allSkipped,
                executable,
                graph.size(),
                skipReasons
        );
    }
}
