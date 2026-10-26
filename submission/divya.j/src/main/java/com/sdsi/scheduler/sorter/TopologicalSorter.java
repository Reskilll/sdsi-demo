package com.sdsi.scheduler.sorter;

import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;

import java.util.*;

/**
 * Milestone 2: Deterministic Topological Sorting via Kahn's Algorithm.
 * Uses adjacency lists and in-degree counts with a PriorityQueue for stable lexicographical tie-breaking.
 * Complexity: O((V + E) log V) time, O(V + E) space.
 */
public class TopologicalSorter {

    /**
     * Produces a valid deterministic execution sequence.
     *
     * @param graph Validated JobGraph
     * @return Deterministic ordered list of job IDs
     * @throws IllegalStateException if a cycle prevents topological sorting
     */
    public List<String> sort(JobGraph graph) {
        if (graph == null || graph.isEmpty()) {
            return Collections.emptyList();
        }

        int totalJobs = graph.size();
        Map<String, Integer> inDegree = new HashMap<>(totalJobs);
        for (String id : graph.getAllJobIds()) {
            inDegree.put(id, graph.getInDegree(id));
        }

        // PriorityQueue guarantees deterministic tie-breaking (lexicographical order)
        PriorityQueue<String> readyQueue = new PriorityQueue<>();
        for (Map.Entry<String, Integer> entry : inDegree.entrySet()) {
            if (entry.getValue() == 0) {
                readyQueue.offer(entry.getKey());
            }
        }

        List<String> executionOrder = new ArrayList<>(totalJobs);

        while (!readyQueue.isEmpty()) {
            String current = readyQueue.poll();
            executionOrder.add(current);

            for (String dependent : graph.getDependents(current)) {
                int updated = inDegree.get(dependent) - 1;
                inDegree.put(dependent, updated);
                if (updated == 0) {
                    readyQueue.offer(dependent);
                }
            }
        }

        if (executionOrder.size() != totalJobs) {
            throw new IllegalStateException("Graph contains a cycle; topological sort cannot be produced. " +
                    "Processed " + executionOrder.size() + " of " + totalJobs + " jobs.");
        }

        return Collections.unmodifiableList(executionOrder);
    }

    /**
     * Invariant Checker: Verifies that every dependency strictly precedes its dependent job.
     */
    public boolean verifyOrder(JobGraph graph, List<String> order) {
        if (order == null || order.size() != graph.size()) {
            return false;
        }

        Map<String, Integer> positionMap = new HashMap<>(order.size());
        for (int i = 0; i < order.size(); i++) {
            positionMap.put(order.get(i), i);
        }

        for (Job job : graph.getJobs().values()) {
            Integer jobPos = positionMap.get(job.getId());
            if (jobPos == null) return false;

            for (String dep : job.getDependsOn()) {
                if (dep == null || dep.trim().isEmpty()) continue;
                Integer depPos = positionMap.get(dep.trim());
                if (depPos == null || depPos >= jobPos) {
                    return false; // Dependency does not precede dependent
                }
            }
        }
        return true;
    }
}
