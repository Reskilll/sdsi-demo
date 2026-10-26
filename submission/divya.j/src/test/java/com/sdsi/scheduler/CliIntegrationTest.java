package com.sdsi.scheduler;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.PrintStream;

import static org.assertj.core.api.Assertions.assertThat;

class CliIntegrationTest {

    @Test
    @DisplayName("CLI: --help displays usage manual and exits with code 0")
    void testHelpFlag() {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();

        int exitCode = Main.run(new String[]{"--help"}, new PrintStream(out), new PrintStream(err));

        assertThat(exitCode).isEqualTo(0);
        assertThat(out.toString()).contains("Usage: java -jar job-scheduler.jar");
    }

    @Test
    @DisplayName("CLI: Default execution runs built-in sample and exits with code 0")
    void testDefaultExecution() {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();

        int exitCode = Main.run(new String[]{}, new PrintStream(out), new PrintStream(err));

        assertThat(exitCode).isEqualTo(0);
        assertThat(out.toString()).contains("All 5 Milestones executed successfully!");
    }

    @Test
    @DisplayName("CLI: Custom file, policy, and failure flags succeed with code 0")
    void testCustomExecution() {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();

        File sampleFile = new File("sample-jobs.json");
        String filePath = sampleFile.exists() ? sampleFile.getAbsolutePath() : "submission/divya.j/sample-jobs.json";

        int exitCode = Main.run(new String[]{
                "--file", filePath,
                "--workers", "3",
                "--policy", "SJF",
                "--fail", "clean_customers"
        }, new PrintStream(out), new PrintStream(err));

        assertThat(exitCode).isEqualTo(0);
        assertThat(out.toString()).contains("Shortest Job First");
    }

    @Test
    @DisplayName("CLI: Rejects cyclic graph with exit code 1")
    void testCyclicGraphRejection() {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();

        File cycleFile = new File("sample-cycle.json");
        String filePath = cycleFile.exists() ? cycleFile.getAbsolutePath() : "submission/divya.j/sample-cycle.json";

        int exitCode = Main.run(new String[]{"--file", filePath}, new PrintStream(out), new PrintStream(err));

        assertThat(exitCode).isEqualTo(1);
        assertThat(err.toString()).contains("Execution halted due to validation failure.");
    }

    @Test
    @DisplayName("CLI: Rejects missing dependencies with exit code 1")
    void testMissingDependenciesRejection() {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();

        File missingFile = new File("sample-missing-dep.json");
        String filePath = missingFile.exists() ? missingFile.getAbsolutePath() : "submission/divya.j/sample-missing-dep.json";

        int exitCode = Main.run(new String[]{"--file", filePath}, new PrintStream(out), new PrintStream(err));

        assertThat(exitCode).isEqualTo(1);
        assertThat(err.toString()).contains("Execution halted due to validation failure.");
    }

    @Test
    @DisplayName("CLI: Rejects invalid worker limit (N < 1) with exit code 2")
    void testInvalidWorkerLimit() {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();

        int exitCode = Main.run(new String[]{"--workers", "0"}, new PrintStream(out), new PrintStream(err));

        assertThat(exitCode).isEqualTo(2);
        assertThat(err.toString()).contains("Worker limit must be >= 1");
    }

    @Test
    @DisplayName("CLI: Rejects non-existent input file with exit code 2")
    void testNonExistentFile() {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();

        int exitCode = Main.run(new String[]{"--file", "non_existent_path_xyz.json"}, new PrintStream(out), new PrintStream(err));

        assertThat(exitCode).isEqualTo(2);
        assertThat(err.toString()).contains("Specified input file not found");
    }
}
