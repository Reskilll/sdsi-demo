package com.sdsi.scheduler;

import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;
import com.sdsi.scheduler.model.ValidationResult;
import com.sdsi.scheduler.validator.GraphValidator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class GraphValidatorTest {

    private GraphValidator validator;

    @BeforeEach
    void setUp() {
        validator = new GraphValidator();
    }

    @Test
    @DisplayName("M1: Valid DAG returns valid result")
    void validDag() {
        List<Job> jobs = List.of(
                new Job("A", 5L, List.of()),
                new Job("B", 3L, List.of("A")),
                new Job("C", 2L, List.of("B"))
        );
        JobGraph graph = new JobGraph(jobs);
        ValidationResult result = validator.validate(graph);

        assertThat(result.isValid()).isTrue();
        assertThat(result.hasCycles()).isFalse();
        assertThat(result.hasMissingDependencies()).isFalse();
        assertThat(result.hasDuplicateDependencies()).isFalse();
    }

    @Test
    @DisplayName("M1: Detect duplicate dependency references (e.g. ['A', 'A'])")
    void detectDuplicateDependencies() {
        List<Job> jobs = List.of(
                new Job("A", 5L, List.of()),
                new Job("B", 3L, List.of("A", "A"))
        );
        JobGraph graph = new JobGraph(jobs);
        ValidationResult result = validator.validate(graph);

        assertThat(result.isValid()).isFalse();
        assertThat(result.hasDuplicateDependencies()).isTrue();
        assertThat(result.getDuplicateDependencies().get("B")).containsExactly("A");
    }

    @Test
    @DisplayName("M1: Detect missing dependencies")
    void detectMissingDependencies() {
        List<Job> jobs = List.of(
                new Job("A", 5L, List.of()),
                new Job("B", 3L, List.of("A", "MISSING_DEP"))
        );
        JobGraph graph = new JobGraph(jobs);
        ValidationResult result = validator.validate(graph);

        assertThat(result.isValid()).isFalse();
        assertThat(result.hasMissingDependencies()).isTrue();
        assertThat(result.getMissingDependencies().get("B")).containsExactly("MISSING_DEP");
    }

    @Test
    @DisplayName("M1: Detect 2-node cycle and report path (A -> B -> A)")
    void detectTwoNodeCycle() {
        List<Job> jobs = List.of(
                new Job("A", 5L, List.of("B")),
                new Job("B", 3L, List.of("A"))
        );
        JobGraph graph = new JobGraph(jobs);
        ValidationResult result = validator.validate(graph);

        assertThat(result.isValid()).isFalse();
        assertThat(result.hasCycles()).isTrue();
        List<List<String>> cycles = result.getDetectedCycles();
        assertThat(cycles).isNotEmpty();
        List<String> cycle = cycles.get(0);
        assertThat(cycle.get(0)).isEqualTo(cycle.get(cycle.size() - 1));
    }

    @Test
    @DisplayName("M1: Detect 3-node cycle and report path (A -> B -> C -> A)")
    void detectThreeNodeCycle() {
        List<Job> jobs = List.of(
                new Job("A", 2L, List.of("C")),
                new Job("B", 3L, List.of("A")),
                new Job("C", 4L, List.of("B")),
                new Job("D", 1L, List.of())
        );
        JobGraph graph = new JobGraph(jobs);
        ValidationResult result = validator.validate(graph);

        assertThat(result.isValid()).isFalse();
        assertThat(result.hasCycles()).isTrue();
        List<List<String>> cycles = result.getDetectedCycles();
        assertThat(cycles).hasSize(1);
        List<String> cycle = cycles.get(0);
        assertThat(cycle).contains("A", "B", "C");
        assertThat(cycle.get(0)).isEqualTo(cycle.get(cycle.size() - 1));
    }

    @Test
    @DisplayName("M1: Detect self-dependency (A -> A)")
    void detectSelfDependency() {
        List<Job> jobs = List.of(
                new Job("A", 5L, List.of("A"))
        );
        JobGraph graph = new JobGraph(jobs);
        ValidationResult result = validator.validate(graph);

        assertThat(result.isValid()).isFalse();
        assertThat(result.getValidationErrors()).anyMatch(err -> err.contains("Self-dependency"));
    }

    @Test
    @DisplayName("M1: Reject negative durations")
    void rejectNegativeDuration() {
        List<Job> jobs = List.of(
                new Job("A", -10L, List.of())
        );
        JobGraph graph = new JobGraph(jobs);
        ValidationResult result = validator.validate(graph);

        assertThat(result.isValid()).isFalse();
        assertThat(result.getValidationErrors()).anyMatch(err -> err.contains("negative duration"));
    }

    @Test
    @DisplayName("M1: Strict mode rejects zero duration if required")
    void strictPositiveDuration() {
        List<Job> jobs = List.of(
                new Job("ZeroJob", 0L, List.of())
        );
        JobGraph graph = new JobGraph(jobs);

        // Allowed in default non-negative mode
        assertThat(validator.validate(graph, false).isValid()).isTrue();

        // Rejected in strictly positive mode
        ValidationResult strictResult = validator.validate(graph, true);
        assertThat(strictResult.isValid()).isFalse();
        assertThat(strictResult.getValidationErrors()).anyMatch(err -> err.contains("strictly positive"));
    }
}
