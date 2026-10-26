package com.sdsi.scheduler.model;

import java.util.*;

/**
 * Encapsulates the validated DAG structure, providing forward and reverse adjacency representations.
 * Complexity: O(V + E) construction.
 */
public class JobGraph {

    private final Map<String, Job> jobs;
    private final Map<String, Set<String>> dependencies;       // jobId -> prerequisites
    private final Map<String, Set<String>> dependents;         // jobId -> downstream jobs (reverse adjacency)
    private final Map<String, List<String>> rawDependencies;   // jobId -> original raw dependency list

    public JobGraph(Collection<Job> jobList) {
        this.jobs = new LinkedHashMap<>();
        this.dependencies = new HashMap<>();
        this.dependents = new HashMap<>();
        this.rawDependencies = new HashMap<>();

        if (jobList != null) {
            Set<String> seenIds = new HashSet<>();
            for (Job job : jobList) {
                if (job == null) {
                    continue;
                }
                String id = job.getId();
                if (id != null) {
                    if (!seenIds.add(id)) {
                        throw new IllegalArgumentException("Duplicate job ID detected during graph construction: '" + id + "'");
                    }
                    this.jobs.put(id, job);
                    this.rawDependencies.put(id, new ArrayList<>(job.getDependsOn()));

                    // Filter non-null and deduplicate for adjacency graph
                    Set<String> uniquePrereqs = new LinkedHashSet<>();
                    for (String dep : job.getDependsOn()) {
                        if (dep != null && !dep.trim().isEmpty()) {
                            uniquePrereqs.add(dep.trim());
                        }
                    }
                    this.dependencies.put(id, uniquePrereqs);
                    this.dependents.putIfAbsent(id, new LinkedHashSet<>());
                }
            }

            // Build reverse adjacency list (dependents)
            for (Map.Entry<String, Set<String>> entry : dependencies.entrySet()) {
                String jobId = entry.getKey();
                for (String dep : entry.getValue()) {
                    dependents.computeIfAbsent(dep, k -> new LinkedHashSet<>()).add(jobId);
                }
            }
        }
    }

    public Map<String, Job> getJobs() {
        return Collections.unmodifiableMap(jobs);
    }

    public Job getJob(String id) {
        return jobs.get(id);
    }

    public boolean containsJob(String id) {
        return id != null && jobs.containsKey(id);
    }

    public Set<String> getAllJobIds() {
        return Collections.unmodifiableSet(jobs.keySet());
    }

    public Set<String> getDependencies(String jobId) {
        return dependencies.getOrDefault(jobId, Collections.emptySet());
    }

    public List<String> getRawDependencies(String jobId) {
        return rawDependencies.getOrDefault(jobId, Collections.emptyList());
    }

    public Set<String> getDependents(String jobId) {
        return dependents.getOrDefault(jobId, Collections.emptySet());
    }

    public int getInDegree(String jobId) {
        return getDependencies(jobId).size();
    }

    public int getOutDegree(String jobId) {
        return getDependents(jobId).size();
    }

    public int size() {
        return jobs.size();
    }

    public boolean isEmpty() {
        return jobs.isEmpty();
    }
}
