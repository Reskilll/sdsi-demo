package com.sdsi.scheduler;

import com.sdsi.scheduler.config.FailurePolicy;
import com.sdsi.scheduler.config.SchedulerConfig;
import com.sdsi.scheduler.engine.DiscreteEventScheduler;
import com.sdsi.scheduler.model.*;
import com.sdsi.scheduler.policy.CriticalPathFirstPolicy;
import com.sdsi.scheduler.policy.FifoPolicy;
import com.sdsi.scheduler.policy.ShortestJobFirstPolicy;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class DiscreteEventSchedulerTest {

    private DiscreteEventScheduler scheduler;

    @BeforeEach
    void setUp() {
        scheduler = new DiscreteEventScheduler();
    }

    @Test
    @DisplayName("M3: FIFO Policy dispatch with 2 workers")
    void testFifoPolicy() {
        List<Job> jobs = List.of(
                new Job("A", 10L, List.of()),
                new Job("B", 4L, List.of()),
                new Job("C", 5L, List.of("B")),
                new Job("D", 2L, List.of("A", "C"))
        );
        JobGraph graph = new JobGraph(jobs);

        SchedulerConfig config = SchedulerConfig.builder()
                .workerLimit(2)
                .schedulingPolicy(new FifoPolicy())
                .build();

        ScheduleResult result = scheduler.schedule(graph, config);

        assertThat(result.getTotalMakespan()).isEqualTo(12L);
        assertThat(result.getWorkerLimit()).isEqualTo(2);
        assertThat(result.getCompletedJobs()).containsExactlyInAnyOrder("A", "B", "C", "D");
        assertThat(result.getWorkerUtilization()).isGreaterThan(0.0);
    }

    @Test
    @DisplayName("M3: Shortest Job First (SJF) prioritizes smaller tasks")
    void testShortestJobFirstPolicy() {
        // Roots: LongRoot (duration 20), ShortRoot (duration 5)
        // With N=1, SJF must schedule ShortRoot first!
        List<Job> jobs = List.of(
                new Job("LongRoot", 20L, List.of()),
                new Job("ShortRoot", 5L, List.of())
        );
        JobGraph graph = new JobGraph(jobs);

        SchedulerConfig config = SchedulerConfig.builder()
                .workerLimit(1)
                .schedulingPolicy(new ShortestJobFirstPolicy())
                .build();

        ScheduleResult result = scheduler.schedule(graph, config);

        assertThat(result.getExecutionOrder()).containsExactly("ShortRoot", "LongRoot");
    }

    @Test
    @DisplayName("M3: Critical Path First policy prioritizes bottleneck chain")
    void testCriticalPathFirstPolicy() {
        // RootA: duration 2 -> ChildA: duration 100 (total path = 102)
        // RootB: duration 5 -> ChildB: duration 10 (total path = 15)
        // With N=1, CriticalPathFirst must schedule RootA first because its downstream path is the project bottleneck!
        List<Job> jobs = List.of(
                new Job("RootA", 2L, List.of()),
                new Job("ChildA", 100L, List.of("RootA")),
                new Job("RootB", 5L, List.of()),
                new Job("ChildB", 10L, List.of("RootB"))
        );
        JobGraph graph = new JobGraph(jobs);

        SchedulerConfig config = SchedulerConfig.builder()
                .workerLimit(1)
                .schedulingPolicy(new CriticalPathFirstPolicy())
                .build();

        ScheduleResult result = scheduler.schedule(graph, config);

        assertThat(result.getExecutionOrder().get(0)).isEqualTo("RootA");
    }

    @Test
    @DisplayName("M3: Simultaneous completions correctly processed and unlock ready jobs")
    void testSimultaneousCompletions() {
        // J1 and J2 both have duration 5 and complete simultaneously at T=5
        // Both unlock J3
        List<Job> jobs = List.of(
                new Job("J1", 5L, List.of()),
                new Job("J2", 5L, List.of()),
                new Job("J3", 3L, List.of("J1", "J2"))
        );
        JobGraph graph = new JobGraph(jobs);

        SchedulerConfig config = SchedulerConfig.builder()
                .workerLimit(2)
                .build();

        ScheduleResult result = scheduler.schedule(graph, config);

        assertThat(result.getTotalMakespan()).isEqualTo(8L);
        JobExecutionState j3State = result.getJobStates().get("J3");
        assertThat(j3State.getStartTime()).isEqualTo(5L);
        assertThat(j3State.getFinishTime()).isEqualTo(8L);
    }

    @Test
    @DisplayName("M3: Zero-duration task processed cleanly without infinite loop")
    void testZeroDurationTask() {
        List<Job> jobs = List.of(
                new Job("InitMarker", 0L, List.of()),
                new Job("RealTask", 5L, List.of("InitMarker"))
        );
        JobGraph graph = new JobGraph(jobs);

        SchedulerConfig config = SchedulerConfig.builder().workerLimit(2).build();
        ScheduleResult result = scheduler.schedule(graph, config);

        assertThat(result.getTotalMakespan()).isEqualTo(5L);
        assertThat(result.getJobStates().get("InitMarker").getStatus()).isEqualTo(JobStatus.COMPLETED);
        assertThat(result.getJobStates().get("RealTask").getStatus()).isEqualTo(JobStatus.COMPLETED);
    }

    @Test
    @DisplayName("M5: Failure propagation in simulation with RUN_TO_COMPLETION")
    void testFailureSimulationRunToCompletion() {
        // A -> B -> C
        // IndependentTask runs in parallel
        List<Job> jobs = List.of(
                new Job("A", 5L, List.of()),
                new Job("B", 5L, List.of("A")),
                new Job("C", 5L, List.of("B")),
                new Job("IndependentTask", 10L, List.of())
        );
        JobGraph graph = new JobGraph(jobs);

        SchedulerConfig config = SchedulerConfig.builder()
                .workerLimit(2)
                .simulatedFailureJobId("A")
                .failurePolicy(FailurePolicy.RUN_TO_COMPLETION)
                .build();

        ScheduleResult result = scheduler.schedule(graph, config);

        assertThat(result.getJobStates().get("A").getStatus()).isEqualTo(JobStatus.FAILED);
        assertThat(result.getJobStates().get("B").getStatus()).isEqualTo(JobStatus.SKIPPED);
        assertThat(result.getJobStates().get("C").getStatus()).isEqualTo(JobStatus.SKIPPED);
        assertThat(result.getJobStates().get("IndependentTask").getStatus()).isEqualTo(JobStatus.COMPLETED);
    }

    @Test
    @DisplayName("M5: Failure propagation in simulation with CANCEL_IMMEDIATELY")
    void testFailureSimulationCancelImmediately() {
        List<Job> jobs = List.of(
                new Job("A", 2L, List.of()),
                new Job("LongRunning", 20L, List.of())
        );
        JobGraph graph = new JobGraph(jobs);

        SchedulerConfig config = SchedulerConfig.builder()
                .workerLimit(2)
                .simulatedFailureJobId("A")
                .failurePolicy(FailurePolicy.CANCEL_IMMEDIATELY)
                .build();

        ScheduleResult result = scheduler.schedule(graph, config);

        assertThat(result.getJobStates().get("A").getStatus()).isEqualTo(JobStatus.FAILED);
        // LongRunning was aborted when A failed at T=2
        assertThat(result.getJobStates().get("LongRunning").getStatus()).isEqualTo(JobStatus.SKIPPED);
        assertThat(result.getTotalMakespan()).isEqualTo(2L);
    }
}
