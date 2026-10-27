package com.sdsi.scheduler;

import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;
import com.sdsi.scheduler.sorter.TopologicalSorter;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class TopologicalSorterTest {

    private TopologicalSorter sorter;

    @BeforeEach
    void setUp() {
        sorter = new TopologicalSorter();
    }

    @Test
    @DisplayName("M2: Produce valid topological order for diamond graph")
    void diamondGraphTopologicalSort() {
        List<Job> jobs = List.of(
                new Job("A", 5L, List.of()),
                new Job("B", 3L, List.of("A")),
                new Job("C", 4L, List.of("A")),
                new Job("D", 2L, List.of("B", "C"))
        );
        JobGraph graph = new JobGraph(jobs);
        List<String> order = sorter.sort(graph);

        assertThat(order).hasSize(4);
        assertThat(sorter.verifyOrder(graph, order)).isTrue();

        // A must come first, D must come last
        assertThat(order.indexOf("A")).isLessThan(order.indexOf("B"));
        assertThat(order.indexOf("A")).isLessThan(order.indexOf("C"));
        assertThat(order.indexOf("B")).isLessThan(order.indexOf("D"));
        assertThat(order.indexOf("C")).isLessThan(order.indexOf("D"));
    }

    @Test
    @DisplayName("M2: Deterministic ordering for concurrent branches")
    void deterministicTieBreaking() {
        // B and C are both ready after A; priority queue sorts them lexicographically
        List<Job> jobs = List.of(
                new Job("A", 1L, List.of()),
                new Job("Z", 1L, List.of("A")),
                new Job("B", 1L, List.of("A"))
        );
        JobGraph graph = new JobGraph(jobs);
        List<String> order = sorter.sort(graph);

        assertThat(order).containsExactly("A", "B", "Z");
    }

    @Test
    @DisplayName("M2: Throws IllegalStateException when graph contains cycle")
    void throwsOnCycle() {
        List<Job> jobs = List.of(
                new Job("X", 2L, List.of("Y")),
                new Job("Y", 3L, List.of("X"))
        );
        JobGraph graph = new JobGraph(jobs);

        assertThatThrownBy(() -> sorter.sort(graph))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("cycle");
    }

    @Test
    @DisplayName("M2: Handles single job and disconnected DAGs")
    void singleAndDisconnected() {
        List<Job> jobs = List.of(
                new Job("alone", 10L, List.of()),
                new Job("G1", 2L, List.of()),
                new Job("G2", 3L, List.of("G1"))
        );
        JobGraph graph = new JobGraph(jobs);
        List<String> order = sorter.sort(graph);

        assertThat(order).hasSize(3);
        assertThat(sorter.verifyOrder(graph, order)).isTrue();
    }
}
