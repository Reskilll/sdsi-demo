package com.sdsi.scheduler;

import com.sdsi.scheduler.failure.FailureSimulator;
import com.sdsi.scheduler.model.FailureReport;
import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class FailureSimulatorTest {

    private FailureSimulator simulator;

    @BeforeEach
    void setUp() {
        simulator = new FailureSimulator();
    }

    @Test
    @DisplayName("M5: Failing a root job skips all downstream dependents")
    void failRootJob() {
        // A -> B -> C
        List<Job> jobs = List.of(
                new Job("A", 1L, List.of()),
                new Job("B", 1L, List.of("A")),
                new Job("C", 1L, List.of("B")),
                new Job("Unrelated", 1L, List.of())
        );
        JobGraph graph = new JobGraph(jobs);

        FailureReport report = simulator.simulateFailure(graph, "A");

        assertThat(report.getFailedJobId()).isEqualTo("A");
        assertThat(report.getDirectDownstreamJobs()).containsExactly("B");
        assertThat(report.getAllSkippedJobs()).containsExactly("B", "C");
        assertThat(report.getExecutableJobs()).containsExactly("Unrelated");
    }

    @Test
    @DisplayName("M5: Failing a branch skips only that branch's descendants")
    void failBranchJob() {
        // Root -> Branch1 -> Join
        //      -> Branch2 -> Join
        //      -> Independent
        List<Job> jobs = List.of(
                new Job("Root", 1L, List.of()),
                new Job("Branch1", 1L, List.of("Root")),
                new Job("Branch2", 1L, List.of("Root")),
                new Job("Join", 1L, List.of("Branch1", "Branch2")),
                new Job("Independent", 1L, List.of())
        );
        JobGraph graph = new JobGraph(jobs);

        // Fail Branch1: Join cannot run because it depends on Branch1!
        // Branch2 and Independent CAN still run!
        FailureReport report = simulator.simulateFailure(graph, "Branch1");

        assertThat(report.getAllSkippedJobs()).containsExactly("Join");
        assertThat(report.getExecutableJobs()).containsExactlyInAnyOrder("Root", "Branch2", "Independent");
    }

    @Test
    @DisplayName("M5: Failing leaf job skips zero downstream jobs")
    void failLeafJob() {
        List<Job> jobs = List.of(
                new Job("Parent", 1L, List.of()),
                new Job("Leaf", 1L, List.of("Parent"))
        );
        JobGraph graph = new JobGraph(jobs);

        FailureReport report = simulator.simulateFailure(graph, "Leaf");

        assertThat(report.getDirectDownstreamJobs()).isEmpty();
        assertThat(report.getAllSkippedJobs()).isEmpty();
        assertThat(report.getExecutableJobs()).containsExactly("Parent");
    }

    @Test
    @DisplayName("M5: Non-existent job ID throws descriptive exception")
    void nonExistentJobThrows() {
        JobGraph graph = new JobGraph(List.of(new Job("A", 1L, List.of())));

        assertThatThrownBy(() -> simulator.simulateFailure(graph, "UNKNOWN_JOB"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("UNKNOWN_JOB");
    }
}
