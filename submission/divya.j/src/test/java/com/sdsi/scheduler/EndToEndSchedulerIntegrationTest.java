package com.sdsi.scheduler;

import com.sdsi.scheduler.model.*;
import com.sdsi.scheduler.service.JobSchedulerService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.*;

class EndToEndSchedulerIntegrationTest {

    private JobSchedulerService service;

    @BeforeEach
    void setUp() {
        service = new JobSchedulerService();
    }

    @Test
    @DisplayName("End-to-end execution of full ETL DAG across all 5 milestones")
    void fullEtlDagIntegration() throws IOException {
        String json = """
                [
                  { "id": "extract_customers", "duration": 5, "dependsOn": [] },
                  { "id": "extract_orders",    "duration": 7, "dependsOn": [] },
                  { "id": "clean_customers",   "duration": 3, "dependsOn": ["extract_customers"] },
                  { "id": "clean_orders",      "duration": 4, "dependsOn": ["extract_orders"] },
                  { "id": "join_data",         "duration": 6, "dependsOn": ["clean_customers", "clean_orders"] },
                  { "id": "aggregate_kpis",    "duration": 4, "dependsOn": ["join_data"] },
                  { "id": "train_model",       "duration": 10, "dependsOn": ["join_data"] },
                  { "id": "generate_report",   "duration": 2, "dependsOn": ["aggregate_kpis"] },
                  { "id": "publish_dashboard", "duration": 3, "dependsOn": ["generate_report", "train_model"] }
                ]
                """;

        JobGraph graph = service.loadFromJson(json);
        assertThat(graph.size()).isEqualTo(9);

        // M1: Validate
        ValidationResult val = service.validate(graph);
        assertThat(val.isValid()).isTrue();

        // M2: Topological sort
        List<String> order = service.getExecutionOrder(graph);
        assertThat(order).hasSize(9);
        // Verify invariant: extract_orders before clean_orders, clean_orders before join_data, etc.
        assertThat(order.indexOf("extract_orders")).isLessThan(order.indexOf("clean_orders"));
        assertThat(order.indexOf("clean_orders")).isLessThan(order.indexOf("join_data"));
        assertThat(order.indexOf("join_data")).isLessThan(order.indexOf("publish_dashboard"));

        // M3: Parallel stages (Worker limit = 2)
        List<Stage> stages = service.groupIntoStages(graph, 2);
        assertThat(stages).isNotEmpty();
        for (Stage s : stages) {
            assertThat(s.getJobIds().size()).isLessThanOrEqualTo(2);
        }

        // M3: Timeline simulation
        SimulationReport sim = service.simulateExecution(graph, 2);
        assertThat(sim.getTotalMakespan()).isGreaterThan(0L);
        assertThat(sim.getScheduledTasks()).hasSize(9);

        // M4: Critical Path
        // Path 1: extract_customers(5) -> clean_customers(3) -> join(6) -> train_model(10) -> publish(3) = 27
        // Path 2: extract_orders(7) -> clean_orders(4) -> join(6) -> train_model(10) -> publish(3) = 30 (Critical!)
        CriticalPathResult cpm = service.computeCriticalPath(graph);
        assertThat(cpm.getMinimumTotalCompletionTime()).isEqualTo(30L);
        assertThat(cpm.getCriticalPath()).containsExactly(
                "extract_orders", "clean_orders", "join_data", "train_model", "publish_dashboard"
        );

        // M5: Failure Simulation
        // If clean_customers fails:
        // Downstream affected: join_data, aggregate_kpis, train_model, generate_report, publish_dashboard
        FailureReport failReport = service.simulateFailure(graph, "clean_customers");
        assertThat(failReport.getAllSkippedJobs()).containsExactlyInAnyOrder(
                "join_data", "aggregate_kpis", "train_model", "generate_report", "publish_dashboard"
        );
        // Surviving executable jobs: extract_customers, extract_orders, clean_orders
        assertThat(failReport.getExecutableJobs()).containsExactlyInAnyOrder(
                "extract_customers", "extract_orders", "clean_orders"
        );
    }

    @Test
    @Timeout(value = 2, unit = TimeUnit.SECONDS)
    @DisplayName("Performance & Scalability: 1,000-node DAG processed within 2 seconds")
    void scalabilityTestLargeDag() {
        // Build 100 levels of 10 nodes each = 1,000 nodes
        int levels = 100;
        int nodesPerLevel = 10;
        List<Job> largeList = new ArrayList<>(levels * nodesPerLevel);

        for (int l = 0; l < levels; l++) {
            for (int i = 0; i < nodesPerLevel; i++) {
                String id = "L" + l + "_N" + i;
                List<String> deps = new ArrayList<>();
                if (l > 0) {
                    // depends on node i and (i+1)%nodesPerLevel from previous level
                    deps.add("L" + (l - 1) + "_N" + i);
                    deps.add("L" + (l - 1) + "_N" + ((i + 1) % nodesPerLevel));
                }
                largeList.add(new Job(id, 2L, deps));
            }
        }

        JobGraph graph = new JobGraph(largeList);
        assertThat(graph.size()).isEqualTo(1000);

        // Validate
        ValidationResult val = service.validate(graph);
        assertThat(val.isValid()).isTrue();

        // Sort
        List<String> order = service.getExecutionOrder(graph);
        assertThat(order).hasSize(1000);

        // Stages with 8 workers
        List<Stage> stages = service.groupIntoStages(graph, 8);
        assertThat(stages).isNotEmpty();

        // Critical Path: 100 levels * 2 duration = 200
        CriticalPathResult cpm = service.computeCriticalPath(graph);
        assertThat(cpm.getMinimumTotalCompletionTime()).isEqualTo(200L);
    }
}
