package com.sdsi.scheduler.service;

import com.sdsi.scheduler.config.SchedulerConfig;
import com.sdsi.scheduler.cpm.CriticalPathAnalyzer;
import com.sdsi.scheduler.engine.DiscreteEventScheduler;
import com.sdsi.scheduler.engine.FailurePropagator;
import com.sdsi.scheduler.model.*;
import com.sdsi.scheduler.parser.InputReader;
import com.sdsi.scheduler.sorter.TopologicalSorter;
import com.sdsi.scheduler.stage.StageScheduler;
import com.sdsi.scheduler.validator.GraphValidator;

import java.io.File;
import java.io.IOException;
import java.util.List;

/**
 * Unified high-level orchestration facade coordinating all scheduler modules.
 */
public class JobSchedulerService {

    private final InputReader inputReader;
    private final GraphValidator validator;
    private final TopologicalSorter sorter;
    private final StageScheduler stageScheduler;
    private final DiscreteEventScheduler discreteEventScheduler;
    private final CriticalPathAnalyzer cpmAnalyzer;
    private final FailurePropagator failurePropagator;

    public JobSchedulerService() {
        this.inputReader = new InputReader();
        this.validator = new GraphValidator();
        this.sorter = new TopologicalSorter();
        this.stageScheduler = new StageScheduler();
        this.discreteEventScheduler = new DiscreteEventScheduler();
        this.cpmAnalyzer = new CriticalPathAnalyzer(this.sorter);
        this.failurePropagator = new FailurePropagator(this.sorter);
    }

    public JobGraph loadFromJson(String json) throws IOException {
        return loadFromJson(json, false);
    }

    public JobGraph loadFromJson(String json, boolean strict) throws IOException {
        List<Job> jobs = inputReader.read(json, strict);
        return new JobGraph(jobs);
    }

    public JobGraph loadFromFile(File file) throws IOException {
        return loadFromFile(file, false);
    }

    public JobGraph loadFromFile(File file, boolean strict) throws IOException {
        List<Job> jobs = inputReader.readFromFile(file, strict);
        return new JobGraph(jobs);
    }

    /**
     * Milestone 1: Graph validation.
     */
    public ValidationResult validate(JobGraph graph) {
        return validator.validate(graph, false);
    }

    public ValidationResult validate(JobGraph graph, boolean requireStrictlyPositiveDuration) {
        return validator.validate(graph, requireStrictlyPositiveDuration);
    }

    /**
     * Milestone 2: Topological Sort.
     */
    public List<String> getExecutionOrder(JobGraph graph) {
        return sorter.sort(graph);
    }

    public boolean verifyTopologicalOrder(JobGraph graph, List<String> order) {
        return sorter.verifyOrder(graph, order);
    }

    /**
     * Milestone 3: Stage Grouping.
     */
    public List<Stage> groupIntoStages(JobGraph graph, int workerLimit) {
        return stageScheduler.groupIntoStages(graph, workerLimit);
    }

    /**
     * Milestone 3: Discrete-Event Timeline Simulation (legacy return).
     */
    public SimulationReport simulateExecution(JobGraph graph, int workerLimit) {
        return stageScheduler.simulateExecution(graph, workerLimit);
    }

    /**
     * Milestone 3 & M5: Full configurable discrete-event simulation.
     */
    public ScheduleResult schedule(JobGraph graph, SchedulerConfig config) {
        return discreteEventScheduler.schedule(graph, config);
    }

    /**
     * Milestone 4: Critical Path Method (CPM).
     */
    public CriticalPathResult computeCriticalPath(JobGraph graph) {
        return cpmAnalyzer.analyze(graph);
    }

    /**
     * Milestone 5: Transitive Failure Propagation.
     */
    public FailureReport simulateFailure(JobGraph graph, String failedJobId) {
        return failurePropagator.propagateFailure(graph, failedJobId);
    }
}
