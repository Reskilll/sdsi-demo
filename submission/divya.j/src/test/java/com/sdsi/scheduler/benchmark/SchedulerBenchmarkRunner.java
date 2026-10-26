package com.sdsi.scheduler.benchmark;

import com.sdsi.scheduler.config.SchedulerConfig;
import com.sdsi.scheduler.cpm.CriticalPathAnalyzer;
import com.sdsi.scheduler.engine.DiscreteEventScheduler;
import com.sdsi.scheduler.engine.FailurePropagator;
import com.sdsi.scheduler.model.Job;
import com.sdsi.scheduler.model.JobGraph;
import com.sdsi.scheduler.policy.CriticalPathFirstPolicy;
import com.sdsi.scheduler.policy.FifoPolicy;
import com.sdsi.scheduler.policy.ShortestJobFirstPolicy;
import com.sdsi.scheduler.sorter.TopologicalSorter;
import com.sdsi.scheduler.validator.GraphValidator;

import java.util.*;

/**
 * Reproducible benchmark harness measuring runtime latency across graph topologies.
 */
public class SchedulerBenchmarkRunner {

    private static final int WARMUP_ROUNDS = 5;
    private static final int MEASURE_ROUNDS = 10;

    public static void main(String[] args) {
        System.out.println("================================================================================");
        System.out.println("   SDSI DAG Job Scheduler - Performance & Scalability Benchmark                 ");
        System.out.println("================================================================================");
        System.out.println("JVM Version : " + System.getProperty("java.version") + " (" + System.getProperty("java.vendor") + ")");
        System.out.println("OS          : " + System.getProperty("os.name") + " " + System.getProperty("os.arch"));
        System.out.println("Warmup      : " + WARMUP_ROUNDS + " iterations | Measurement: " + MEASURE_ROUNDS + " iterations\n");

        Map<String, List<Job>> topologies = new LinkedHashMap<>();
        topologies.put("1. Long Dependency Chain (V=1,000, E=999)", createLongChain(1000));
        topologies.put("2. Wide Independent Layers (V=1,000, E=0)", createWideIndependent(1000));
        topologies.put("3. Diamond Lattice Graph (V=1,000, E=1,800)", createDiamondLattice(100, 10));
        topologies.put("4. High Fan-In / Fan-Out (V=1,000, E=2,500)", createHighFanInOut(1000));
        topologies.put("5. Large Sparse DAG (V=2,000, E=4,000)", createSparseDag(2000, 4));

        GraphValidator validator = new GraphValidator();
        TopologicalSorter sorter = new TopologicalSorter();
        CriticalPathAnalyzer cpmAnalyzer = new CriticalPathAnalyzer();
        DiscreteEventScheduler scheduler = new DiscreteEventScheduler();
        FailurePropagator propagator = new FailurePropagator();

        for (Map.Entry<String, List<Job>> entry : topologies.entrySet()) {
            String name = entry.getKey();
            List<Job> jobList = entry.getValue();

            System.out.println("--------------------------------------------------------------------------------");
            System.out.println("Benchmark Topology: " + name);
            System.out.println("--------------------------------------------------------------------------------");

            // 1. Graph Construction
            long constructNs = benchmarkOperation(() -> new JobGraph(jobList));
            JobGraph graph = new JobGraph(jobList);

            // 2. Validation / Cycle Detection
            long validateNs = benchmarkOperation(() -> validator.validate(graph));

            // 3. Topological Sort
            long sortNs = benchmarkOperation(() -> sorter.sort(graph));

            // 4. Critical Path Analysis
            long cpmNs = benchmarkOperation(() -> cpmAnalyzer.analyze(graph));

            // 5. Discrete-Event Scheduling (FIFO, 4 Workers)
            SchedulerConfig fifoConfig = SchedulerConfig.builder().workerLimit(4).schedulingPolicy(new FifoPolicy()).build();
            long fifoScheduleNs = benchmarkOperation(() -> scheduler.schedule(graph, fifoConfig));

            // 6. Discrete-Event Scheduling (SJF, 4 Workers)
            SchedulerConfig sjfConfig = SchedulerConfig.builder().workerLimit(4).schedulingPolicy(new ShortestJobFirstPolicy()).build();
            long sjfScheduleNs = benchmarkOperation(() -> scheduler.schedule(graph, sjfConfig));

            // 7. Discrete-Event Scheduling (Critical Path First, 4 Workers)
            SchedulerConfig cpConfig = SchedulerConfig.builder().workerLimit(4).schedulingPolicy(new CriticalPathFirstPolicy()).build();
            long cpScheduleNs = benchmarkOperation(() -> scheduler.schedule(graph, cpConfig));

            // 8. Failure Propagation from root node
            String rootJob = graph.getAllJobIds().iterator().next();
            long failNs = benchmarkOperation(() -> propagator.propagateFailure(graph, rootJob));

            System.out.printf("  %-35s : %8.3f ms%n", "Graph Construction", constructNs / 1_000_000.0);
            System.out.printf("  %-35s : %8.3f ms%n", "Cycle Detection & Validation (M1)", validateNs / 1_000_000.0);
            System.out.printf("  %-35s : %8.3f ms%n", "Topological Sort (M2)", sortNs / 1_000_000.0);
            System.out.printf("  %-35s : %8.3f ms%n", "Critical Path Method (M4)", cpmNs / 1_000_000.0);
            System.out.printf("  %-35s : %8.3f ms%n", "Simulation FIFO (M3)", fifoScheduleNs / 1_000_000.0);
            System.out.printf("  %-35s : %8.3f ms%n", "Simulation SJF (M3)", sjfScheduleNs / 1_000_000.0);
            System.out.printf("  %-35s : %8.3f ms%n", "Simulation CP-First (M3)", cpScheduleNs / 1_000_000.0);
            System.out.printf("  %-35s : %8.3f ms%n", "Failure Propagation (M5)", failNs / 1_000_000.0);
            System.out.println();
        }
    }

    private static long benchmarkOperation(Runnable action) {
        // Warmup
        for (int i = 0; i < WARMUP_ROUNDS; i++) {
            action.run();
        }
        // Measurement
        long start = System.nanoTime();
        for (int i = 0; i < MEASURE_ROUNDS; i++) {
            action.run();
        }
        long end = System.nanoTime();
        return (end - start) / MEASURE_ROUNDS;
    }

    private static List<Job> createLongChain(int size) {
        List<Job> jobs = new ArrayList<>(size);
        for (int i = 0; i < size; i++) {
            String id = "Chain_" + i;
            List<String> deps = (i == 0) ? Collections.emptyList() : Collections.singletonList("Chain_" + (i - 1));
            jobs.add(new Job(id, 2L, deps));
        }
        return jobs;
    }

    private static List<Job> createWideIndependent(int size) {
        List<Job> jobs = new ArrayList<>(size);
        for (int i = 0; i < size; i++) {
            jobs.add(new Job("Independent_" + i, 5L, Collections.emptyList()));
        }
        return jobs;
    }

    private static List<Job> createDiamondLattice(int levels, int width) {
        List<Job> jobs = new ArrayList<>(levels * width);
        for (int l = 0; l < levels; l++) {
            for (int w = 0; w < width; w++) {
                String id = "L" + l + "_W" + w;
                List<String> deps = new ArrayList<>();
                if (l > 0) {
                    deps.add("L" + (l - 1) + "_W" + w);
                    deps.add("L" + (l - 1) + "_W" + ((w + 1) % width));
                }
                jobs.add(new Job(id, 3L, deps));
            }
        }
        return jobs;
    }

    private static List<Job> createHighFanInOut(int size) {
        List<Job> jobs = new ArrayList<>(size);
        // 10 hub roots -> 980 workers -> 10 sink aggregators
        for (int i = 0; i < 10; i++) {
            jobs.add(new Job("HubRoot_" + i, 2L, Collections.emptyList()));
        }
        List<String> rootDeps = new ArrayList<>();
        for (int i = 0; i < 10; i++) rootDeps.add("HubRoot_" + i);

        for (int i = 0; i < size - 20; i++) {
            jobs.add(new Job("Worker_" + i, 4L, Collections.singletonList("HubRoot_" + (i % 10))));
        }
        for (int i = 0; i < 10; i++) {
            List<String> sinkDeps = new ArrayList<>();
            for (int k = i; k < size - 20; k += 10) {
                sinkDeps.add("Worker_" + k);
            }
            jobs.add(new Job("Sink_" + i, 3L, sinkDeps));
        }
        return jobs;
    }

    private static List<Job> createSparseDag(int size, int maxDeps) {
        Random rand = new Random(42);
        List<Job> jobs = new ArrayList<>(size);
        for (int i = 0; i < size; i++) {
            String id = "Sparse_" + i;
            List<String> deps = new ArrayList<>();
            if (i > 0) {
                int count = rand.nextInt(Math.min(i, maxDeps) + 1);
                Set<Integer> chosen = new HashSet<>();
                while (chosen.size() < count) {
                    chosen.add(rand.nextInt(i));
                }
                for (int c : chosen) {
                    deps.add("Sparse_" + c);
                }
            }
            jobs.add(new Job(id, 1L + rand.nextInt(10), deps));
        }
        return jobs;
    }
}
