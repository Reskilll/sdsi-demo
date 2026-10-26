package com.sdsi.scheduler;

import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.parser.JobJsonParser;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.util.List;

import static org.assertj.core.api.Assertions.*;

class JobJsonParserTest {

    private JobJsonParser parser;

    @BeforeEach
    void setUp() {
        parser = new JobJsonParser();
    }

    @Test
    @DisplayName("Parse standard JSON array of jobs")
    void parseStandardArray() throws IOException {
        String json = """
                [
                  { "id": "job1", "duration": 10, "dependsOn": [] },
                  { "id": "job2", "duration": 20, "dependsOn": ["job1"] }
                ]
                """;
        List<Job> jobs = parser.parse(json);
        assertThat(jobs).hasSize(2);
        assertThat(jobs.get(0).getId()).isEqualTo("job1");
        assertThat(jobs.get(0).getDuration()).isEqualTo(10L);
        assertThat(jobs.get(1).getDependsOn()).containsExactly("job1");
    }

    @Test
    @DisplayName("Parse wrapped object with 'jobs' array")
    void parseWrappedObject() throws IOException {
        String json = """
                {
                  "jobs": [
                    { "id": "build", "duration": 15, "dependsOn": [] }
                  ]
                }
                """;
        List<Job> jobs = parser.parse(json);
        assertThat(jobs).hasSize(1);
        assertThat(jobs.get(0).getId()).isEqualTo("build");
        assertThat(jobs.get(0).getDuration()).isEqualTo(15L);
    }

    @Test
    @DisplayName("Parse key-value map format")
    void parseMapFormat() throws IOException {
        String json = """
                {
                  "lint": { "duration": 5, "dependsOn": [] },
                  "test": { "duration": 12, "dependsOn": ["lint"] }
                }
                """;
        List<Job> jobs = parser.parse(json);
        assertThat(jobs).hasSize(2);
        assertThat(jobs).extracting(Job::getId).containsExactlyInAnyOrder("lint", "test");
    }

    @Test
    @DisplayName("Supports aliases: 'name', 'time', 'dependencies'")
    void parseAliases() throws IOException {
        String json = """
                [
                  { "name": "compile", "time": 8, "dependencies": ["setup"] }
                ]
                """;
        List<Job> jobs = parser.parse(json);
        assertThat(jobs).hasSize(1);
        assertThat(jobs.get(0).getId()).isEqualTo("compile");
        assertThat(jobs.get(0).getDuration()).isEqualTo(8L);
        assertThat(jobs.get(0).getDependsOn()).containsExactly("setup");
    }

    @Test
    @DisplayName("Detect duplicate job IDs and throw descriptive error")
    void rejectDuplicateJobIds() {
        String json = """
                [
                  { "id": "taskA", "duration": 5, "dependsOn": [] },
                  { "id": "taskA", "duration": 8, "dependsOn": [] }
                ]
                """;
        assertThatThrownBy(() -> parser.parse(json))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Duplicate job ID detected");
    }

    @Test
    @DisplayName("Handle empty or null input gracefully")
    void handleEmptyInput() throws IOException {
        assertThat(parser.parse("")).isEmpty();
        assertThat(parser.parse("   ")).isEmpty();
        assertThat(parser.parse(null)).isEmpty();
        assertThat(parser.parse("[]")).isEmpty();
    }
}
