package com.sdsi.scheduler.policy;

import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;

import java.util.*;

/**
 * Longest Remaining Critical Path First policy.
 * Precomputes the longest remaining duration from each job to any terminal sink
 * using dynamic programming in O(V + E). Jobs on the critical path are prioritized earliest.
 * Ties are broken deterministically by job ID.
 */
public class CriticalPathFirstPolicy implements SchedulingPolicy {

    @Override
    public String getName() {
        return "Critical Path First (Longest Remaining Path to Sink)";
    }

    @Override
    public Comparator<String> createComparator(JobGraph graph) {
        Map<String, Long> remainingPathMap = precomputeRemainingPaths(graph);

        return (id1, id2) -> {
            long p1 = remainingPathMap.getOrDefault(id1, 0L);
            long p2 = remainingPathMap.getOrDefault(id2, 0L);

            // Descending order (largest remaining critical duration first)
            int cmp = Long.compare(p2, p1);
            if (cmp != 0) {
                return cmp;
            }
            return id1.compareTo(id2); // deterministic tie-break
        };
    }

    private Map<String, Long> precomputeRemainingPaths(JobGraph graph) {
        Map<String, Long> remaining = new HashMap<>(graph.size());
        // Reverse topological traversal or memoized recursion over DAG
        for (String id : graph.getAllJobIds()) {
            computePathMemo(id, graph, remaining, new HashSet<>());
        }
        return remaining;
    }

    private long computePathMemo(String id, JobGraph graph, Map<String, Long> memo, Set<String> visiting) {
        if (memo.containsKey(id)) {
            return memo.get(id);
        }
        if (!visiting.add(id)) {
            // Cycle guard: return 0 if cycles present during preliminary computation
            return 0L;
        }

        Job job = graph.getJob(id);
        long myDuration = job != null ? job.getDuration() : 0L;

        long maxDownstream = 0L;
        for (String dependent : graph.getDependents(id)) {
            long downstreamPath = computePathMemo(dependent, graph, memo, visiting);
            if (downstreamPath > maxDownstream) {
                maxDownstream = downstreamPath;
            }
        }

        visiting.remove(id);
        long total = Math.addExact(myDuration, maxDownstream);
        memo.put(id, total);
        return total;
    }
}
