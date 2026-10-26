package com.sdsi.scheduler;

import com.sdsi.scheduler.config.FailurePolicy;
import com.sdsi.scheduler.config.SchedulerConfig;
import com.sdsi.scheduler.model.*;
import com.sdsi.scheduler.policy.CriticalPathFirstPolicy;
import com.sdsi.scheduler.policy.FifoPolicy;
import com.sdsi.scheduler.policy.SchedulingPolicy;
import com.sdsi.scheduler.policy.ShortestJobFirstPolicy;
import com.sdsi.scheduler.service.JobSchedulerService;

import java.io.File;
import java.io.PrintStream;
import java.util.List;

/**
 * Hardened Command Line Interface and Entry Point for the DAG Job Scheduler.
 */
public class Main {

    public static final String DEFAULT_SAMPLE_JSON = """
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

    public static void main(String[] args) {
        int exitCode = run(args, System.out, System.err);
        if (exitCode != 0) {
            System.exit(exitCode);
        }
    }

    public static int run(String[] args, PrintStream out, PrintStream err) {
        String filePath = null;
        int workerLimit = 2;
        String failJobId = null;
        SchedulingPolicy policy = new FifoPolicy();
        FailurePolicy failurePolicy = FailurePolicy.RUN_TO_COMPLETION;
        boolean strictSchema = false;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--file":
                case "-f":
                    if (i + 1 < args.length) filePath = args[++i];
                    break;
                case "--workers":
                case "-w":
                    if (i + 1 < args.length) {
                        try {
                            workerLimit = Integer.parseInt(args[++i]);
                            if (workerLimit < 1) {
                                err.println("Error: Worker limit must be >= 1, received: " + workerLimit);
                                return 2;
                            }
                        } catch (NumberFormatException e) {
                            err.println("Error: Worker limit must be a valid integer.");
                            return 2;
                        }
                    }
                    break;
                case "--policy":
                case "-p":
                    if (i + 1 < args.length) {
                        String p = args[++i].toUpperCase();
                        switch (p) {
                            case "SJF":
                            case "SHORTEST":
                                policy = new ShortestJobFirstPolicy();
                                break;
                            case "CP":
                            case "CRITICAL":
                            case "CRITICAL_PATH":
                                policy = new CriticalPathFirstPolicy();
                                break;
                            case "FIFO":
                            default:
                                policy = new FifoPolicy();
                                break;
                        }
                    }
                    break;
                case "--failure-mode":
                    if (i + 1 < args.length) {
                        String m = args[++i].toUpperCase();
                        if ("CANCEL_IMMEDIATELY".equals(m) || "CANCEL".equals(m)) {
                            failurePolicy = FailurePolicy.CANCEL_IMMEDIATELY;
                        } else {
                            failurePolicy = FailurePolicy.RUN_TO_COMPLETION;
                        }
                    }
                    break;
                case "--fail":
                    if (i + 1 < args.length) failJobId = args[++i];
                    break;
                case "--strict":
                    strictSchema = true;
                    break;
                case "--help":
                case "-h":
                    printUsage(out);
                    return 0;
                default:
                    err.println("Unknown argument: " + args[i]);
                    printUsage(err);
                    return 2;
            }
        }

        out.println("================================================================================");
        out.println("   SDSI Mini ETL / Build Orchestrator - DAG Job Scheduler (PS5)                ");
        out.println("================================================================================");

        JobSchedulerService service = new JobSchedulerService();
        JobGraph graph;

        try {
            if (filePath != null) {
                File file = new File(filePath);
                if (!file.exists()) {
                    err.println("Error: Specified input file not found: " + file.getAbsolutePath());
                    return 2;
                }
                out.println("Loading JSON from: " + file.getAbsolutePath());
                graph = service.loadFromFile(file, strictSchema);
            } else {
                out.println("No input file specified via --file. Running built-in ETL pipeline sample.");
                graph = service.loadFromJson(DEFAULT_SAMPLE_JSON, strictSchema);
            }

            out.println("Loaded " + graph.size() + " jobs successfully.\n");

            // Milestone 1: Validation
            out.println("--------------------------------------------------------------------------------");
            out.println("[M1] GRAPH VALIDATION & INTEGRITY CHECK");
            out.println("--------------------------------------------------------------------------------");
            ValidationResult validation = service.validate(graph);
            out.println(validation);

            if (!validation.isValid()) {
                err.println("\nExecution halted due to validation failure.");
                return 1;
            }

            // Milestone 2: Topological Sort
            out.println("\n--------------------------------------------------------------------------------");
            out.println("[M2] TOPOLOGICAL SORT (Valid Sequential Execution Order)");
            out.println("--------------------------------------------------------------------------------");
            List<String> order = service.getExecutionOrder(graph);
            for (int i = 0; i < order.size(); i++) {
                out.printf("  Step %2d: %s (duration: %d)%n",
                        (i + 1), order.get(i), graph.getJob(order.get(i)).getDuration());
            }

            // Milestone 4: Critical Path Method (CPM)
            out.println("\n--------------------------------------------------------------------------------");
            out.println("[M4] CRITICAL PATH METHOD (CPM) & LOWER-BOUND MAKESPAN");
            out.println("--------------------------------------------------------------------------------");
            CriticalPathResult cpm = service.computeCriticalPath(graph);
            out.println(cpm);
            out.println("\nJob Timing Breakdown (ES = Early Start, EF = Early Finish, Slack):");
            for (String jobId : order) {
                long es = cpm.getEarlyStartTimes().getOrDefault(jobId, 0L);
                long ef = cpm.getEarlyFinishTimes().getOrDefault(jobId, 0L);
                long slack = cpm.getSlackTimes().getOrDefault(jobId, 0L);
                boolean isCrit = cpm.getCriticalPath().contains(jobId);
                out.printf("  - %-20s : ES=%2d, EF=%2d, Slack=%2d %s%n",
                        jobId, es, ef, slack, (isCrit ? "[CRITICAL]" : ""));
            }

            // Milestone 3: Discrete-Event Parallel Scheduling
            out.println("\n--------------------------------------------------------------------------------");
            out.printf("[M3] PARALLEL SCHEDULING (Workers N = %d, Policy = %s)%n", workerLimit, policy.getName());
            out.println("--------------------------------------------------------------------------------");
            SchedulerConfig config = SchedulerConfig.builder()
                    .workerLimit(workerLimit)
                    .schedulingPolicy(policy)
                    .failurePolicy(failurePolicy)
                    .simulatedFailureJobId(failJobId)
                    .build();

            ScheduleResult scheduleResult = service.schedule(graph, config);
            out.println(scheduleResult);

            // Milestone 5: Failure Simulation
            out.println("\n--------------------------------------------------------------------------------");
            out.println("[M5] FAILURE IMPACT SIMULATION");
            out.println("--------------------------------------------------------------------------------");
            String targetFail = failJobId != null ? failJobId : "clean_customers";
            if (!graph.containsJob(targetFail)) {
                targetFail = order.get(0);
            }
            FailureReport failureReport = service.simulateFailure(graph, targetFail);
            out.println(failureReport);

            out.println("\n================================================================================");
            out.println("   All 5 Milestones executed successfully!                                      ");
            out.println("================================================================================");
            return 0;

        } catch (Exception e) {
            err.println("\nERROR: " + e.getMessage());
            return 1;
        }
    }

    private static void printUsage(PrintStream out) {
        out.println("Usage: java -jar job-scheduler.jar [OPTIONS]");
        out.println("Options:");
        out.println("  -f, --file <path>          Path to JSON job specification file");
        out.println("  -w, --workers <N>          Maximum concurrent workers (default: 2)");
        out.println("  -p, --policy <FIFO|SJF|CP> Scheduling policy (FIFO, SJF, CP; default: FIFO)");
        out.println("  --fail <jobId>             Simulate failure of specified job ID");
        out.println("  --failure-mode <MODE>      Failure mode (RUN_TO_COMPLETION or CANCEL_IMMEDIATELY)");
        out.println("  --strict                   Enforce strict schema validation (reject unknown properties)");
        out.println("  -h, --help                 Display this manual");
    }
}
