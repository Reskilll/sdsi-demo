package com.sdsi.scheduler;

import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;
import com.sdsi.scheduler.model.SimulationReport;
import com.sdsi.scheduler.model.Stage;
import com.sdsi.scheduler.stage.StageScheduler;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class StageSchedulerTest {

    private StageScheduler scheduler;

    @BeforeEach
    void setUp() {
        scheduler = new StageScheduler();
    }

    @Test
    @DisplayName("M3: Group jobs into stages with worker limit N=2")
    void groupIntoStagesWithWorkerLimit() {
        // Roots: R1, R2, R3, R4 (4 independent roots)
        // With N=2, Stage 1 will have [R1, R2], Stage 2 will have [R3, R4]
        List<Job> jobs = List.of(
                new Job("R1", 5L, List.of()),
                new Job("R2", 5L, List.of()),
                new Job("R3", 5L, List.of()),
                new Job("R4", 5L, List.of()),
                new Job("Child", 2L, List.of("R1", "R2", "R3", "R4"))
        );
        JobGraph graph = new JobGraph(jobs);

        List<Stage> stages = scheduler.groupIntoStages(graph, 2);

        // Max workers per stage must be <= 2
        for (Stage stage : stages) {
            assertThat(stage.getJobIds().size()).isLessThanOrEqualTo(2);
        }

        // Child must be in the final stage
        Stage lastStage = stages.get(stages.size() - 1);
        assertThat(lastStage.getJobIds()).containsExactly("Child");
    }

    @Test
    @DisplayName("M3: Discrete-event simulation with 2 workers")
    void simulateExecutionTimeline() {
        // A(10) and B(4) run in parallel on Worker 1 and Worker 2.
        // B finishes at T=4. Next ready job C(5, dependsOn B) starts immediately on Worker 2 at T=4, finishes at T=9.
        // A finishes at T=10.
        // D(2, dependsOn A, C) starts at max(10, 9) = 10, finishes at T=12.
        List<Job> jobs = List.of(
                new Job("A", 10L, List.of()),
                new Job("B", 4L, List.of()),
                new Job("C", 5L, List.of("B")),
                new Job("D", 2L, List.of("A", "C"))
        );
        JobGraph graph = new JobGraph(jobs);

        SimulationReport report = scheduler.simulateExecution(graph, 2);

        assertThat(report.getTotalMakespan()).isEqualTo(12L);
        assertThat(report.getScheduledTasks()).hasSize(4);
    }

    @Test
    @DisplayName("M3: Worker limit N=1 executes purely sequentially")
    void workerLimitOneIsSequential() {
        List<Job> jobs = List.of(
                new Job("J1", 3L, List.of()),
                new Job("J2", 4L, List.of()),
                new Job("J3", 2L, List.of())
        );
        JobGraph graph = new JobGraph(jobs);

        SimulationReport report = scheduler.simulateExecution(graph, 1);
        assertThat(report.getTotalMakespan()).isEqualTo(3L + 4L + 2L);
    }

    @Test
    @DisplayName("M3: Invalid worker limit throws IllegalArgumentException")
    void invalidWorkerLimit() {
        JobGraph graph = new JobGraph(List.of(new Job("A", 1L, List.of())));
        assertThatThrownBy(() -> scheduler.groupIntoStages(graph, 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> scheduler.simulateExecution(graph, -2))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
