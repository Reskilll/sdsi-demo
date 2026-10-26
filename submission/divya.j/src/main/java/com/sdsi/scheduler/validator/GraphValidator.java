package com.sdsi.scheduler.validator;

import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;
import com.sdsi.scheduler.model.ValidationResult;

import java.util.*;

/**
 * Milestone 1: Comprehensive Graph Validation.
 * - Detects duplicate, blank, or null job IDs
 * - Validates positive or non-negative durations
 * - Detects missing dependencies and duplicate dependency entries
 * - Detects self-dependencies (A -> A)
 * - Detects directed cycles and reports the exact cycle path (e.g. A -> B -> C -> A)
 * - Handles empty graphs and disconnected components
 * Complexity: O(V + E)
 */
public class GraphValidator {

    private enum Color {
        WHITE, // Unvisited
        GRAY,  // Visiting (in active recursion stack)
        BLACK  // Visited
    }

    public ValidationResult validate(JobGraph graph) {
        return validate(graph, false);
    }

    public ValidationResult validate(JobGraph graph, boolean requireStrictlyPositiveDuration) {
        if (graph == null || graph.isEmpty()) {
            return new ValidationResult(false, Collections.emptyMap(), Collections.emptyMap(),
                    Collections.emptyList(), Collections.singletonList("Graph is empty or null."));
        }

        List<String> validationErrors = new ArrayList<>();
        Map<String, List<String>> missingDependencies = new LinkedHashMap<>();
        Map<String, List<String>> duplicateDependencies = new LinkedHashMap<>();

        // 1. Validate node integrity, durations, and dependency constraints
        for (Job job : graph.getJobs().values()) {
            String jobId = job.getId();
            if (jobId == null || jobId.trim().isEmpty()) {
                validationErrors.add("Encountered job with null or blank ID.");
                continue;
            }

            if (requireStrictlyPositiveDuration && job.getDuration() <= 0) {
                validationErrors.add("Job '" + jobId + "' duration must be strictly positive (> 0), but found: " + job.getDuration());
            } else if (job.getDuration() < 0) {
                validationErrors.add("Job '" + jobId + "' has negative duration: " + job.getDuration());
            }

            // Inspect raw dependencies for duplicates, nulls, self-loops, and missing IDs
            List<String> rawDeps = graph.getRawDependencies(jobId);
            Set<String> seenDepsInJob = new HashSet<>();
            List<String> dupesInJob = new ArrayList<>();

            for (String dep : rawDeps) {
                if (dep == null || dep.trim().isEmpty()) {
                    validationErrors.add("Job '" + jobId + "' references a null or blank dependency.");
                    continue;
                }
                String cleanDep = dep.trim();
                if (!seenDepsInJob.add(cleanDep)) {
                    dupesInJob.add(cleanDep);
                }

                if (cleanDep.equals(jobId)) {
                    validationErrors.add("Self-dependency detected: Job '" + jobId + "' depends on itself.");
                } else if (!graph.containsJob(cleanDep)) {
                    missingDependencies.computeIfAbsent(jobId, k -> new ArrayList<>()).add(cleanDep);
                }
            }

            if (!dupesInJob.isEmpty()) {
                duplicateDependencies.put(jobId, dupesInJob);
            }
        }

        // 2. Cycle Detection using 3-Color DFS
        List<List<String>> detectedCycles = detectCycles(graph);

        boolean isValid = validationErrors.isEmpty()
                && missingDependencies.isEmpty()
                && duplicateDependencies.isEmpty()
                && detectedCycles.isEmpty();

        return new ValidationResult(isValid, missingDependencies, duplicateDependencies, detectedCycles, validationErrors);
    }

    private List<List<String>> detectCycles(JobGraph graph) {
        Map<String, Color> colors = new HashMap<>(graph.size());
        for (String id : graph.getAllJobIds()) {
            colors.put(id, Color.WHITE);
        }

        List<List<String>> cycles = new ArrayList<>();
        Set<String> normalizedSignatures = new HashSet<>();
        List<String> currentPath = new ArrayList<>();

        // Sort keys for deterministic traversal
        List<String> sortedJobIds = new ArrayList<>(graph.getAllJobIds());
        Collections.sort(sortedJobIds);

        for (String startNode : sortedJobIds) {
            if (colors.get(startNode) == Color.WHITE) {
                dfsCycleFinder(startNode, graph, colors, currentPath, cycles, normalizedSignatures);
            }
        }

        return cycles;
    }

    private void dfsCycleFinder(
            String current,
            JobGraph graph,
            Map<String, Color> colors,
            List<String> currentPath,
            List<List<String>> cycles,
            Set<String> normalizedSignatures
    ) {
        colors.put(current, Color.GRAY);
        currentPath.add(current);

        // Execution direction: current node executes before its downstream dependents
        List<String> downstream = new ArrayList<>(graph.getDependents(current));
        Collections.sort(downstream);

        for (String next : downstream) {
            Color nextColor = colors.get(next);
            if (nextColor == Color.GRAY) {
                // Cycle back-edge detected! Reconstruct exact path
                int cycleStartIndex = currentPath.indexOf(next);
                if (cycleStartIndex != -1) {
                    List<String> cyclePath = new ArrayList<>(currentPath.subList(cycleStartIndex, currentPath.size()));
                    cyclePath.add(next); // close cycle

                    String signature = canonicalCycleSignature(cyclePath);
                    if (normalizedSignatures.add(signature)) {
                        cycles.add(cyclePath);
                    }
                }
            } else if (nextColor == Color.WHITE) {
                dfsCycleFinder(next, graph, colors, currentPath, cycles, normalizedSignatures);
            }
        }

        currentPath.remove(currentPath.size() - 1);
        colors.put(current, Color.BLACK);
    }

    private String canonicalCycleSignature(List<String> cycle) {
        if (cycle.size() <= 1) {
            return String.join("->", cycle);
        }
        List<String> nodes = cycle.subList(0, cycle.size() - 1);
        int n = nodes.size();
        if (n == 0) return "";

        String minNode = Collections.min(nodes);
        int minIndex = nodes.indexOf(minNode);

        List<String> rotated = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            rotated.add(nodes.get((minIndex + i) % n));
        }
        rotated.add(rotated.get(0));
        return String.join("->", rotated);
    }
}
