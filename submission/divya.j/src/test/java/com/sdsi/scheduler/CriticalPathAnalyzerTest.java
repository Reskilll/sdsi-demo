package com.sdsi.scheduler;

import com.sdsi.scheduler.cpm.CriticalPathAnalyzer;
import com.sdsi.scheduler.model.CriticalPathResult;
import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class CriticalPathAnalyzerTest {

    private CriticalPathAnalyzer analyzer;

    @BeforeEach
    void setUp() {
        analyzer = new CriticalPathAnalyzer();
    }

    @Test
    @DisplayName("M4: Compute critical path on diamond graph")
    void diamondGraphCriticalPath() {
        // A (5)
        //   -> B (4) -> D (2) (Path A -> B -> D = 11)
        //   -> C (6) -> D (2) (Path A -> C -> D = 13, Critical)
        List<Job> jobs = List.of(
                new Job("A", 5L, List.of()),
                new Job("B", 4L, List.of("A")),
                new Job("C", 6L, List.of("A")),
                new Job("D", 2L, List.of("B", "C"))
        );
        JobGraph graph = new JobGraph(jobs);

        CriticalPathResult result = analyzer.analyze(graph);

        assertThat(result.getMinimumTotalCompletionTime()).isEqualTo(13L);
        assertThat(result.getCriticalPath()).containsExactly("A", "C", "D");

        assertThat(result.getEarlyStartTimes().get("A")).isEqualTo(0L);
        assertThat(result.getEarlyFinishTimes().get("A")).isEqualTo(5L);
        assertThat(result.getEarlyStartTimes().get("C")).isEqualTo(5L);
        assertThat(result.getEarlyFinishTimes().get("C")).isEqualTo(11L);
        assertThat(result.getEarlyStartTimes().get("D")).isEqualTo(11L);
        assertThat(result.getEarlyFinishTimes().get("D")).isEqualTo(13L);

        // B has slack: Slack = 2
        assertThat(result.getSlackTimes().get("B")).isEqualTo(2L);
        assertThat(result.getSlackTimes().get("A")).isEqualTo(0L);
        assertThat(result.getSlackTimes().get("C")).isEqualTo(0L);
        assertThat(result.getSlackTimes().get("D")).isEqualTo(0L);
    }

    @Test
    @DisplayName("M4: Deterministic tie-breaking when multiple critical paths have equal length")
    void multipleEqualCriticalPathsTieBreak() {
        // A(5) -> BranchB(5) -> Sink(2) = 12
        // A(5) -> BranchC(5) -> Sink(2) = 12
        // Predecessor tie between BranchB and BranchC must resolve deterministically to BranchB (lexicographical)
        List<Job> jobs = List.of(
                new Job("A", 5L, List.of()),
                new Job("BranchB", 5L, List.of("A")),
                new Job("BranchC", 5L, List.of("A")),
                new Job("Sink", 2L, List.of("BranchB", "BranchC"))
        );
        JobGraph graph = new JobGraph(jobs);

        CriticalPathResult result = analyzer.analyze(graph);

        assertThat(result.getMinimumTotalCompletionTime()).isEqualTo(12L);
        assertThat(result.getCriticalPath()).containsExactly("A", "BranchB", "Sink");
    }

    @Test
    @DisplayName("M4: Disjoint parallel paths")
    void disjointPathsCriticalPath() {
        List<Job> jobs = List.of(
                new Job("X1", 10L, List.of()),
                new Job("X2", 15L, List.of("X1")), // total 25
                new Job("Y1", 8L, List.of()),
                new Job("Y2", 20L, List.of("Y1"))  // total 28 (critical)
        );
        JobGraph graph = new JobGraph(jobs);

        CriticalPathResult result = analyzer.analyze(graph);

        assertThat(result.getMinimumTotalCompletionTime()).isEqualTo(28L);
        assertThat(result.getCriticalPath()).containsExactly("Y1", "Y2");
    }

    @Test
    @DisplayName("M4: Single job graph")
    void singleJob() {
        JobGraph graph = new JobGraph(List.of(new Job("solo", 42L, List.of())));
        CriticalPathResult result = analyzer.analyze(graph);

        assertThat(result.getMinimumTotalCompletionTime()).isEqualTo(42L);
        assertThat(result.getCriticalPath()).containsExactly("solo");
    }
}
