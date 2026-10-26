package com.sdsi.scheduler;

import com.sdsi.scheduler.benchmark.SchedulerBenchmarkRunner;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import static org.assertj.core.api.Assertions.assertThat;

class SchedulerBenchmarkTest {

    @Test
    @DisplayName("Benchmark suite executes successfully across all 5 graph topologies")
    void testBenchmarkHarness() {
        PrintStream orig = System.out;
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try {
            System.setOut(new PrintStream(out));
            SchedulerBenchmarkRunner.main(new String[]{});
        } finally {
            System.setOut(orig);
        }

        String output = out.toString();
        assertThat(output).contains("SDSI DAG Job Scheduler - Performance & Scalability Benchmark");
        assertThat(output).contains("1. Long Dependency Chain");
        assertThat(output).contains("2. Wide Independent Layers");
        assertThat(output).contains("3. Diamond Lattice Graph");
        assertThat(output).contains("4. High Fan-In / Fan-Out");
        assertThat(output).contains("5. Large Sparse DAG");
        assertThat(output).contains("Cycle Detection & Validation (M1)");
        assertThat(output).contains("Critical Path Method (M4)");
    }
}
