package com.sdsi.scheduler.cpm;

import com.sdsi.scheduler.model.CriticalPathResult;
import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;
import com.sdsi.scheduler.sorter.TopologicalSorter;

import java.util.*;

/**
 * Milestone 4: Critical Path Method (CPM) and Project Duration Lower-Bound Analysis.
 * Implements standard dual-pass dynamic programming:
 * - Forward Pass: Early Start (ES) & Early Finish (EF)
 * - Backward Pass: Late Start (LS) & Late Finish (LF)
 * - Float Calculation: Slack = LS - ES (Slack == 0 denotes critical jobs)
 * Complexity: O(V + E)
 */
public class CriticalPathAnalyzer {

    private final TopologicalSorter sorter;

    public CriticalPathAnalyzer() {
        this(new TopologicalSorter());
    }

    public CriticalPathAnalyzer(TopologicalSorter sorter) {
        this.sorter = Objects.requireNonNull(sorter, "TopologicalSorter cannot be null");
    }

    public CriticalPathResult analyze(JobGraph graph) {
        if (graph == null || graph.isEmpty()) {
            return new CriticalPathResult(Collections.emptyList(), 0L,
                    Collections.emptyMap(), Collections.emptyMap(),
                    Collections.emptyMap(), Collections.emptyMap(), Collections.emptyMap());
        }

        List<String> topoOrder = sorter.sort(graph);

        Map<String, Long> earlyStart = new HashMap<>(graph.size());
        Map<String, Long> earlyFinish = new HashMap<>(graph.size());
        Map<String, String> bestPredecessor = new HashMap<>(graph.size());

        // 1. Forward Pass (Calculates ES, EF, and tracks longest predecessor with deterministic tie-breaking)
        long totalCompletionTime = 0L;
        String terminalCriticalNode = null;

        for (String jobId : topoOrder) {
            Job job = graph.getJob(jobId);
            long duration = job != null ? job.getDuration() : 0L;

            long maxPrereqFinish = 0L;
            String bestPred = null;

            // Sort prerequisites for deterministic traversal
            List<String> sortedPrereqs = new ArrayList<>(graph.getDependencies(jobId));
            Collections.sort(sortedPrereqs);

            for (String prereq : sortedPrereqs) {
                long prereqEf = earlyFinish.getOrDefault(prereq, 0L);
                if (prereqEf > maxPrereqFinish) {
                    maxPrereqFinish = prereqEf;
                    bestPred = prereq;
                } else if (prereqEf == maxPrereqFinish && maxPrereqFinish > 0) {
                    // Deterministic tie-breaker: choose lexicographically smaller predecessor
                    if (bestPred == null || prereq.compareTo(bestPred) < 0) {
                        bestPred = prereq;
                    }
                }
            }

            long es = maxPrereqFinish;
            long ef = Math.addExact(es, duration);

            earlyStart.put(jobId, es);
            earlyFinish.put(jobId, ef);
            if (bestPred != null) {
                bestPredecessor.put(jobId, bestPred);
            }

            if (ef > totalCompletionTime) {
                totalCompletionTime = ef;
                terminalCriticalNode = jobId;
            } else if (ef == totalCompletionTime && terminalCriticalNode != null) {
                // Deterministic tie-breaker for terminal sink
                if (jobId.compareTo(terminalCriticalNode) < 0) {
                    terminalCriticalNode = jobId;
                }
            } else if (terminalCriticalNode == null) {
                terminalCriticalNode = jobId;
            }
        }

        // 2. Backward Pass (Calculates LF, LS, and Slack)
        Map<String, Long> lateFinish = new HashMap<>(graph.size());
        Map<String, Long> lateStart = new HashMap<>(graph.size());
        Map<String, Long> slacks = new HashMap<>(graph.size());

        // Sinks default to total completion time
        for (String jobId : topoOrder) {
            if (graph.getDependents(jobId).isEmpty()) {
                lateFinish.put(jobId, totalCompletionTime);
            }
        }

        // Traverse in reverse topological order
        for (int i = topoOrder.size() - 1; i >= 0; i--) {
            String jobId = topoOrder.get(i);
            Job job = graph.getJob(jobId);
            long duration = job != null ? job.getDuration() : 0L;

            Set<String> dependents = graph.getDependents(jobId);
            if (!dependents.isEmpty()) {
                long minLateStart = Long.MAX_VALUE;
                for (String dep : dependents) {
                    Long depLs = lateStart.get(dep);
                    if (depLs != null && depLs < minLateStart) {
                        minLateStart = depLs;
                    }
                }
                lateFinish.put(jobId, minLateStart);
            }

            long lf = lateFinish.getOrDefault(jobId, totalCompletionTime);
            long ls = lf - duration;
            lateStart.put(jobId, ls);

            long slack = ls - earlyStart.getOrDefault(jobId, 0L);
            slacks.put(jobId, slack);
        }

        // 3. Reconstruct Critical Path by backtracking from terminal node
        List<String> criticalPath = new ArrayList<>();
        String current = terminalCriticalNode;
        while (current != null) {
            criticalPath.add(current);
            current = bestPredecessor.get(current);
        }
        Collections.reverse(criticalPath);

        return new CriticalPathResult(
                criticalPath,
                totalCompletionTime,
                earlyStart,
                earlyFinish,
                lateStart,
                lateFinish,
                slacks
        );
    }
}
