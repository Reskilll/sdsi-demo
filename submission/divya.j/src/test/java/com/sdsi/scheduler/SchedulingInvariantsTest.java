package com.sdsi.scheduler;

import com.sdsi.scheduler.config.SchedulerConfig;
import com.sdsi.scheduler.engine.DiscreteEventScheduler;
import com.sdsi.scheduler.model.*;
import com.sdsi.scheduler.policy.FifoPolicy;
import com.sdsi.scheduler.policy.ShortestJobFirstPolicy;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;

import java.util.*;

import static org.assertj.core.api.Assertions.*;

class SchedulingInvariantsTest {

    private final DiscreteEventScheduler scheduler = new DiscreteEventScheduler();

    @Test
    @DisplayName("Invariant: Determinism across repeated executions with identical configuration")
    void testDeterminism() {
        JobGraph graph = generateRandomDag(50, 4, 12345L);
        SchedulerConfig config = SchedulerConfig.builder().workerLimit(3).build();

        ScheduleResult run1 = scheduler.schedule(graph, config);
        ScheduleResult run2 = scheduler.schedule(graph, config);

        assertThat(run1.getTotalMakespan()).isEqualTo(run2.getTotalMakespan());
        assertThat(run1.getExecutionOrder()).isEqualTo(run2.getExecutionOrder());
        for (int i = 0; i < run1.getScheduledTasks().size(); i++) {
            ScheduledTask t1 = run1.getScheduledTasks().get(i);
            ScheduledTask t2 = run2.getScheduledTasks().get(i);
            assertThat(t1.getJobId()).isEqualTo(t2.getJobId());
            assertThat(t1.getStartTime()).isEqualTo(t2.getStartTime());
            assertThat(t1.getEndTime()).isEqualTo(t2.getEndTime());
            assertThat(t1.getWorkerId()).isEqualTo(t2.getWorkerId());
        }
    }

    @RepeatedTest(5)
    @DisplayName("Invariants on Randomly Generated DAGs: Dependency order, Concurrency limit N, Makespan >= Critical Path")
    void testInvariantsOnRandomDags() {
        Random rng = new Random();
        int nodeCount = 30 + rng.nextInt(30);
        int maxDeps = 3;
        long seed = rng.nextLong();
        JobGraph graph = generateRandomDag(nodeCount, maxDeps, seed);

        int workerLimit = 1 + rng.nextInt(5);
        SchedulerConfig config = SchedulerConfig.builder()
                .workerLimit(workerLimit)
                .schedulingPolicy(rng.nextBoolean() ? new FifoPolicy() : new ShortestJobFirstPolicy())
                .build();

        ScheduleResult result = scheduler.schedule(graph, config);

        // Invariant 1: Makespan must be at least the critical-path theoretical lower bound
        assertThat(result.getTotalMakespan()).isGreaterThanOrEqualTo(result.getCriticalPathDuration());

        // Invariant 2: No job starts before all its dependencies have finished
        Map<String, JobExecutionState> states = result.getJobStates();
        for (Job job : graph.getJobs().values()) {
            JobExecutionState state = states.get(job.getId());
            assertThat(state.getStatus()).isEqualTo(JobStatus.COMPLETED);
            assertThat(state.getFinishTime()).isGreaterThanOrEqualTo(state.getStartTime());

            for (String depId : job.getDependsOn()) {
                JobExecutionState depState = states.get(depId);
                assertThat(depState.getFinishTime()).isLessThanOrEqualTo(state.getStartTime());
            }
        }

        // Invariant 3: Concurrency bound N at every instant
        List<ScheduledTask> tasks = result.getScheduledTasks();
        long makespan = result.getTotalMakespan();

        // Check concurrency across all interval boundary points
        Set<Long> checkpoints = new TreeSet<>();
        for (ScheduledTask t : tasks) {
            checkpoints.add(t.getStartTime());
            checkpoints.add(t.getEndTime());
        }

        for (long t : checkpoints) {
            long runningCount = tasks.stream()
                    .filter(task -> task.getStartTime() <= t && t < task.getEndTime())
                    .count();
            assertThat(runningCount).isLessThanOrEqualTo(workerLimit);
        }

        // Invariant 4: Every job scheduled at most once
        Set<String> scheduledIds = new HashSet<>();
        for (ScheduledTask t : tasks) {
            assertThat(scheduledIds.add(t.getJobId())).isTrue();
        }
        assertThat(scheduledIds).hasSize(graph.size());
    }

    private JobGraph generateRandomDag(int nodeCount, int maxDeps, long seed) {
        Random rand = new Random(seed);
        List<Job> jobs = new ArrayList<>(nodeCount);

        for (int i = 0; i < nodeCount; i++) {
            String id = "Node_" + String.format("%03d", i);
            long duration = 1L + rand.nextInt(15);
            List<String> deps = new ArrayList<>();

            if (i > 0) {
                int depCount = rand.nextInt(Math.min(i, maxDeps) + 1);
                Set<Integer> chosen = new HashSet<>();
                while (chosen.size() < depCount) {
                    chosen.add(rand.nextInt(i)); // strictly lower index guarantees DAG
                }
                for (int c : chosen) {
                    deps.add("Node_" + String.format("%03d", c));
                }
            }
            jobs.add(new Job(id, duration, deps));
        }
        return new JobGraph(jobs);
    }
}
